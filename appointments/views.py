import json
from datetime import timedelta

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from doctors.models import Doctor
from consultations.models import FollowUp

from .forms import AppointmentForm, AttachmentUploadForm
from .models import Appointment, AppointmentAttachment, AppointmentMessage
from .models import Appointment, DoctorReview
from .forms import DoctorReviewForm


def _is_admin_user(user):
    return getattr(user, "user_type", "") == "admin" or user.is_staff


def _get_doctor_for_user(user):
    return Doctor.objects.filter(user=user).first()


def _get_appointment_doctor_user(appointment):
    return getattr(appointment.doctor, "user", None)


def _user_can_access_appointment_sync(user, appointment):
    if not user.is_authenticated:
        return False

    if _is_admin_user(user):
        return True

    if appointment.patient_id == user.id:
        return True

    doctor = _get_doctor_for_user(user)
    if doctor and appointment.doctor_id == doctor.id:
        return True

    return False


def _get_first_doctor_message(appointment):
    doctor_user = _get_appointment_doctor_user(appointment)
    if not doctor_user:
        return None

    return (
        AppointmentMessage.objects
        .filter(appointment=appointment, sender=doctor_user)
        .order_by("created_at", "id")
        .first()
    )


def _get_chat_timing_data(appointment):
    """
    منطق الشات:
    - الطبيب هو من يبدأ الشات.
    - عند أول رسالة من الطبيب تبدأ جلسة 15 دقيقة.
    - عند عمل متابعة يمكن إعادة فتح نفس الشات عبر reset_chat_session().
    - إذا كانت chat_started_at محفوظة في Appointment نعتمد عليها مباشرة.
    - fallback للرسائل القديمة قبل إضافة الحقول: أول رسالة من الطبيب.
    """
    now = timezone.now()

    # الحالة الجديدة المعتمدة على حقول الموعد
    if appointment.chat_started_at:
        started_at = appointment.chat_started_at
        expires_at = appointment.chat_expires_at or (started_at + timedelta(minutes=15))
        chat_closed = now > expires_at
        remaining_seconds = max(int((expires_at - now).total_seconds()), 0)

        return {
            "doctor_started_chat": True,
            "started_at": started_at,
            "expires_at": expires_at,
            "chat_open": not chat_closed,
            "chat_closed": chat_closed,
            "remaining_seconds": remaining_seconds,
        }

    # fallback للبيانات القديمة إذا كان الطبيب بدأ سابقاً قبل إضافة الحقول
    first_doctor_message = _get_first_doctor_message(appointment)
    if first_doctor_message:
        started_at = first_doctor_message.created_at
        expires_at = started_at + timedelta(minutes=15)
        chat_closed = now > expires_at
        remaining_seconds = max(int((expires_at - now).total_seconds()), 0)

        return {
            "doctor_started_chat": True,
            "started_at": started_at,
            "expires_at": expires_at,
            "chat_open": not chat_closed,
            "chat_closed": chat_closed,
            "remaining_seconds": remaining_seconds,
        }

    # الطبيب لم يبدأ بعد
    return {
        "doctor_started_chat": False,
        "started_at": None,
        "expires_at": None,
        "chat_open": True,
        "chat_closed": False,
        "remaining_seconds": None,
    }


def _can_user_send_message(user, appointment):
    """
    القواعد:
    - الطبيب يستطيع بدء الشات
    - المريض لا يستطيع الإرسال قبل أول رسالة من الطبيب
    - بعد مرور 15 دقيقة من بداية الجلسة يمنع الإرسال على الجميع
    """
    if not _user_can_access_appointment_sync(user, appointment):
        return False, "ليس لديك صلاحية للوصول إلى هذه المحادثة."

    timing = _get_chat_timing_data(appointment)

    doctor = _get_doctor_for_user(user)
    is_doctor = doctor and appointment.doctor_id == doctor.id
    is_patient = appointment.patient_id == user.id
    is_admin = _is_admin_user(user)

    if timing["chat_closed"]:
        return False, "انتهت مدة المحادثة (15 دقيقة)."

    if is_admin:
        return True, ""

    if is_doctor:
        return True, ""

    if is_patient and not timing["doctor_started_chat"]:
        return False, "لا يمكنك إرسال رسالة قبل أن يبدأ الطبيب المحادثة."

    return True, ""


@login_required
def booking_create(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.doctor = doctor
            appointment.patient = request.user

            full_name = (appointment.full_name or "").strip()
            if not full_name:
                appointment.full_name = (
                    f"{request.user.first_name} {request.user.last_name}".strip()
                    or request.user.username
                )

            if not appointment.phone and getattr(request.user, "phone", None):
                appointment.phone = request.user.phone

            if not appointment.email and request.user.email:
                appointment.email = request.user.email

            appointment.save()
            messages.success(request, "تم إرسال طلب الحجز بنجاح.")
            return redirect("booking_success", appointment_id=appointment.id)
    else:
        form = AppointmentForm(
            initial={
                "full_name": f"{request.user.first_name} {request.user.last_name}".strip(),
                "phone": getattr(request.user, "phone", "") or "",
                "email": request.user.email or "",
            }
        )

    return render(
        request,
        "appointments/booking.html",
        {
            "doctor": doctor,
            "form": form,
        },
    )


@login_required
def booking_success(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user,
    )
    return render(
        request,
        "appointments/booking_success.html",
        {
            "appointment": appointment,
        },
    )


@login_required
def appointment_list(request):
    appointments = Appointment.objects.select_related("doctor", "patient")

    if not _is_admin_user(request.user):
        doctor = _get_doctor_for_user(request.user)
        if doctor:
            appointments = appointments.filter(doctor=doctor)
        else:
            appointments = appointments.filter(patient=request.user)

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        appointments = appointments.filter(full_name__icontains=q)

    if status:
        appointments = appointments.filter(status=status)

    appointments = appointments.order_by("-id")

    context = {
        "appointments": appointments,
        "q": q,
        "selected_status": status,
    }
    return render(request, "appointments/appointment_list.html", context)


@login_required
def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("doctor", "patient").prefetch_related("attachments", "followups"),
        id=appointment_id,
    )

    if not _user_can_access_appointment_sync(request.user, appointment):
        messages.error(request, "ليس لديك صلاحية للوصول إلى هذا الموعد.")
        return redirect("appointment_list")

    upload_form = AttachmentUploadForm()
    chat_timing = _get_chat_timing_data(appointment)

    followups = appointment.followups.all().order_by("-created_at")
    can_create_followup = FollowUp.can_create_for_appointment(appointment)
    followup_deadline = FollowUp.get_followup_deadline_for_appointment(appointment)

    return render(
        request,
        "appointments/appointment_detail.html",
        {
            "appointment": appointment,
            "upload_form": upload_form,
            "chat_timing": chat_timing,
            "followups": followups,
            "can_create_followup": can_create_followup,
            "followup_deadline": followup_deadline,
        },
    )


@login_required
def doctor_appointment_detail(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related("doctor", "patient").prefetch_related("attachments", "followups"),
        id=pk,
    )

    if not _user_can_access_appointment_sync(request.user, appointment):
        messages.error(request, "ليس لديك صلاحية للوصول إلى هذا الموعد.")
        return redirect("appointment_list")

    upload_form = AttachmentUploadForm()
    chat_timing = _get_chat_timing_data(appointment)

    followups = appointment.followups.all().order_by("-created_at")
    can_create_followup = FollowUp.can_create_for_appointment(appointment)
    followup_deadline = FollowUp.get_followup_deadline_for_appointment(appointment)

    return render(
        request,
        "appointments/appointment_detail.html",
        {
            "appointment": appointment,
            "upload_form": upload_form,
            "chat_timing": chat_timing,
            "followups": followups,
            "can_create_followup": can_create_followup,
            "followup_deadline": followup_deadline,
        },
    )


@login_required
def upload_appointment_attachment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if not _user_can_access_appointment_sync(request.user, appointment):
        messages.error(request, "ليس لديك صلاحية لرفع ملفات لهذا الموعد.")
        return redirect("appointment_list")

    if request.method == "POST":
        form = AttachmentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.appointment = appointment
            attachment.uploaded_by = request.user

            if not attachment.title:
                attachment.title = attachment.file.name

            attachment.save()
            messages.success(request, "تم رفع الملف الطبي بنجاح.")
        else:
            messages.error(request, "تعذر رفع الملف. تأكد من تعبئة البيانات بشكل صحيح.")

    return redirect("appointment_detail", appointment_id=appointment.id)


class AppointmentChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.appointment_id = self.scope["url_route"]["kwargs"]["appointment_id"]
        self.room_group_name = f"appointment_chat_{self.appointment_id}"

        if not self.user.is_authenticated:
            await self.close()
            return

        allowed = await self.user_can_access_appointment()
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        timing = await self.get_chat_timing_data()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_status",
                    "doctor_started_chat": timing["doctor_started_chat"],
                    "chat_open": timing["chat_open"],
                    "chat_closed": timing["chat_closed"],
                    "remaining_seconds": timing["remaining_seconds"],
                    "expires_at": timing["expires_at"].strftime("%Y-%m-%d %H:%M:%S") if timing["expires_at"] else None,
                }
            )
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (TypeError, json.JSONDecodeError):
            return

        content = (data.get("message") or "").strip()
        if not content:
            return

        can_send, error_message = await self.can_current_user_send_message()
        if not can_send:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": error_message,
                    }
                )
            )
            return

        message = await self.save_message(content)
        timing = await self.get_chat_timing_data()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message["content"],
                "sender": message["sender"],
                "sender_type": message["sender_type"],
                "created_at": message["created_at"],
                "doctor_started_chat": timing["doctor_started_chat"],
                "chat_open": timing["chat_open"],
                "chat_closed": timing["chat_closed"],
                "remaining_seconds": timing["remaining_seconds"],
                "expires_at": timing["expires_at"].strftime("%Y-%m-%d %H:%M:%S") if timing["expires_at"] else None,
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_message",
                    "message": event["message"],
                    "sender": event["sender"],
                    "sender_type": event["sender_type"],
                    "created_at": event["created_at"],
                    "doctor_started_chat": event.get("doctor_started_chat"),
                    "chat_open": event.get("chat_open"),
                    "chat_closed": event.get("chat_closed"),
                    "remaining_seconds": event.get("remaining_seconds"),
                    "expires_at": event.get("expires_at"),
                }
            )
        )

    @sync_to_async
    def user_can_access_appointment(self):
        try:
            appointment = Appointment.objects.select_related("patient", "doctor").get(id=self.appointment_id)
        except Appointment.DoesNotExist:
            return False

        return _user_can_access_appointment_sync(self.user, appointment)

    @sync_to_async
    def can_current_user_send_message(self):
        try:
            appointment = Appointment.objects.select_related("patient", "doctor").get(id=self.appointment_id)
        except Appointment.DoesNotExist:
            return False, "الموعد غير موجود."

        return _can_user_send_message(self.user, appointment)

    @sync_to_async
    def get_chat_timing_data(self):
        try:
            appointment = Appointment.objects.select_related("doctor").get(id=self.appointment_id)
        except Appointment.DoesNotExist:
            return {
                "doctor_started_chat": False,
                "started_at": None,
                "expires_at": None,
                "chat_open": False,
                "chat_closed": True,
                "remaining_seconds": 0,
            }

        return _get_chat_timing_data(appointment)

    @sync_to_async
    def save_message(self, content):
        appointment = Appointment.objects.select_related("doctor").get(id=self.appointment_id)

        sender_type = "patient"
        doctor = Doctor.objects.filter(user=self.user).first()
        if doctor and appointment.doctor_id == doctor.id:
            sender_type = "doctor"
        elif _is_admin_user(self.user):
            sender_type = "admin"

        # الطبيب فقط يبدأ الجلسة الجديدة
        if sender_type == "doctor":
            if not appointment.chat_started_at or (
                appointment.chat_expires_at and timezone.now() > appointment.chat_expires_at
            ):
                appointment.start_chat_session()

        msg = AppointmentMessage.objects.create(
            appointment=appointment,
            sender=self.user,
            content=content,
        )

        return {
            "content": msg.content,
            "sender": self.user.get_full_name().strip() or self.user.username,
            "sender_type": sender_type,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M"),
        }


@login_required
def appointment_chat(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("doctor", "patient").prefetch_related("messages__sender"),
        id=appointment_id,
    )

    if not _user_can_access_appointment_sync(request.user, appointment):
        messages.error(request, "ليس لديك صلاحية للوصول إلى محادثة هذا الموعد.")
        return redirect("appointment_list")

    doctor_user = getattr(appointment.doctor, "user", None)
    messages_qs = appointment.messages.select_related("sender").all().order_by("created_at", "id")
    chat_timing = _get_chat_timing_data(appointment)

    current_user_can_send, send_error_message = _can_user_send_message(request.user, appointment)

    prepared_messages = []
    for msg in messages_qs:
        sender_type = "patient"

        if doctor_user and msg.sender_id == doctor_user.id:
            sender_type = "doctor"
        elif _is_admin_user(msg.sender):
            sender_type = "admin"

        prepared_messages.append(
            {
                "sender_name": msg.sender.get_full_name().strip() or msg.sender.username,
                "content": msg.content,
                "created_at": msg.created_at,
                "sender_type": sender_type,
            }
        )

    return render(
        request,
        "appointments/appointment_chat.html",
        {
            "appointment": appointment,
            "chat_messages": prepared_messages,
            "chat_timing": chat_timing,
            "current_user_can_send": current_user_can_send,
            "send_error_message": send_error_message,
        },
    )


@login_required
def submit_doctor_review(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("doctor", "patient"),
        id=appointment_id,
        patient=request.user
    )

    if hasattr(appointment, "review"):
        messages.warning(request, "لقد قمت بتقييم هذه الجلسة مسبقاً.")
        return redirect("appointment_detail", appointment_id=appointment.id)

    chat_timing = _get_chat_timing_data(appointment)

    if not chat_timing["doctor_started_chat"]:
        messages.error(request, "لا يمكنك تقييم الطبيب قبل بدء الجلسة.")
        return redirect("appointment_chat", appointment_id=appointment.id)

    if not chat_timing["chat_closed"]:
        messages.error(request, "لا يمكنك التقييم قبل انتهاء الجلسة.")
        return redirect("appointment_chat", appointment_id=appointment.id)

    if request.method == "POST":
        form = DoctorReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.appointment = appointment
            review.doctor = appointment.doctor
            review.patient = request.user
            review.save()

            messages.success(request, "تم إرسال التقييم بنجاح ✅")
            return redirect("appointment_detail", appointment_id=appointment.id)
    else:
        form = DoctorReviewForm()

    return render(request, "appointments/submit_doctor_review.html", {
        "form": form,
        "appointment": appointment,
    })
