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
from .models import DoctorReview
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


# 🔥 أهم تعديل في المشروع
def _get_chat_timing_data(appointment):
    now = timezone.now()

    if appointment.chat_started_at:
        started_at = appointment.chat_started_at
        expires_at = appointment.chat_expires_at or (started_at + timedelta(minutes=15))

        chat_closed = now > expires_at
        remaining_seconds = max(int((expires_at - now).total_seconds()), 0)

        # ✅ إنهاء الجلسة تلقائياً
        if chat_closed and appointment.session_status != "completed":
            appointment.session_status = "completed"
            appointment.save(update_fields=["session_status"])

        return {
            "doctor_started_chat": True,
            "started_at": started_at,
            "expires_at": expires_at,
            "chat_open": not chat_closed,
            "chat_closed": chat_closed,
            "remaining_seconds": remaining_seconds,
        }

    first_doctor_message = _get_first_doctor_message(appointment)
    if first_doctor_message:
        started_at = first_doctor_message.created_at
        expires_at = started_at + timedelta(minutes=15)

        chat_closed = now > expires_at
        remaining_seconds = max(int((expires_at - now).total_seconds()), 0)

        # ✅ إنهاء الجلسة تلقائياً
        if chat_closed and appointment.session_status != "completed":
            appointment.session_status = "completed"
            appointment.save(update_fields=["session_status"])

        return {
            "doctor_started_chat": True,
            "started_at": started_at,
            "expires_at": expires_at,
            "chat_open": not chat_closed,
            "chat_closed": chat_closed,
            "remaining_seconds": remaining_seconds,
        }

    return {
        "doctor_started_chat": False,
        "started_at": None,
        "expires_at": None,
        "chat_open": True,
        "chat_closed": False,
        "remaining_seconds": None,
    }


def _can_user_send_message(user, appointment):
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

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = (data.get("message") or "").strip()

        if not content:
            return

        can_send, error_message = await self.can_current_user_send_message()
        if not can_send:
            await self.send(json.dumps({"type": "error", "message": error_message}))
            return

        message = await self.save_message(content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message["content"],
                "sender": message["sender"],
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @sync_to_async
    def user_can_access_appointment(self):
        appointment = Appointment.objects.get(id=self.appointment_id)
        return _user_can_access_appointment_sync(self.user, appointment)

    @sync_to_async
    def can_current_user_send_message(self):
        appointment = Appointment.objects.get(id=self.appointment_id)
        return _can_user_send_message(self.user, appointment)

    @sync_to_async
    def save_message(self, content):
        appointment = Appointment.objects.get(id=self.appointment_id)

        sender_type = "patient"
        doctor = Doctor.objects.filter(user=self.user).first()

        if doctor and appointment.doctor_id == doctor.id:
            sender_type = "doctor"

        if sender_type == "doctor":
            if not appointment.chat_started_at:
                appointment.start_chat_session()

        msg = AppointmentMessage.objects.create(
            appointment=appointment,
            sender=self.user,
            content=content,
        )

        return {
            "content": msg.content,
            "sender": self.user.username,
            "sender_type": sender_type,
        }
        @login_required
def appointment_list(request):
    appointments = Appointment.objects.select_related("doctor", "patient")

    if not _is_admin_user(request.user):
        doctor = _get_doctor_for_user(request.user)
        if doctor:
            appointments = appointments.filter(doctor=doctor)
        else:
            appointments = appointments.filter(patient=request.user)

    appointments = appointments.order_by("-id")

    return render(
        request,
        "appointments/appointment_list.html",
        {
            "appointments": appointments,
        },
    )
