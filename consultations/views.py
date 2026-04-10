from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from appointments.models import Appointment
from .forms import FollowUpAttachmentForm, FollowUpForm
from .models import FollowUp


def _is_admin_user(user):
    return getattr(user, "user_type", "") == "admin" or user.is_staff


def _validate_followup_creation_access(request, appointment):
    """
    التحقق من صلاحية إنشاء متابعة على استشارة معينة.
    يرجع None إذا كل شيء صحيح.
    ويرجع redirect response إذا يوجد سبب يمنع الإنشاء.
    """

    if not appointment:
        messages.error(request, "الاستشارة الأصلية غير موجودة.")
        return redirect("consultations:followup_list")

    # المتابعة للمريض فقط
    if appointment.patient_id != request.user.id and not _is_admin_user(request.user):
        messages.error(request, "المتابعة الطبية متاحة للمريض صاحب الاستشارة فقط.")
        return redirect("appointment_detail", appointment_id=appointment.pk)

    # لازم الاستشارة تكون مكتملة
    if appointment.session_status != "completed":
        messages.error(request, "لا يمكن إنشاء متابعة قبل اكتمال الاستشارة الأصلية.")
        return redirect("appointment_detail", appointment_id=appointment.pk)

    # منع المتابعة بعد 14 يوم
    if not FollowUp.can_create_for_appointment(appointment):
        messages.error(
            request,
            "انتهت مدة المتابعة لهذه الاستشارة، ولا يمكن إنشاء متابعة إلا بعد طلب استشارة جديدة."
        )
        return redirect("appointment_detail", appointment_id=appointment.pk)

    return None


@login_required
def followup_list(request):
    followups_qs = FollowUp.objects.select_related(
        "appointment",
        "patient",
        "doctor"
    ).order_by("-created_at")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    method = request.GET.get("method", "").strip()
    date = request.GET.get("date", "").strip()

    if q:
        followups_qs = followups_qs.filter(
            Q(appointment__full_name__icontains=q) |
            Q(patient__username__icontains=q) |
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q) |
            Q(doctor__name__icontains=q) |
            Q(appointment__phone__icontains=q) |
            Q(appointment__email__icontains=q)
        )

    if status:
        followups_qs = followups_qs.filter(status=status)

    if method:
        followups_qs = followups_qs.filter(method=method)

    if date:
        followups_qs = followups_qs.filter(followup_date=date)

    if not _is_admin_user(request.user):
        # المريض يرى متابعاته فقط، والطبيب يرى المتابعات المرتبطة به
        doctor = getattr(request.user, "doctor_profile", None)
        if doctor:
            followups_qs = followups_qs.filter(doctor=doctor)
        else:
            followups_qs = followups_qs.filter(patient=request.user)

    paginator = Paginator(followups_qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    stats_base_qs = followups_qs
    stats = {
        "total": stats_base_qs.count(),
        "scheduled": stats_base_qs.filter(status="scheduled").count(),
        "completed": stats_base_qs.filter(status="completed").count(),
        "cancelled": stats_base_qs.filter(status="cancelled").count(),
    }

    context = {
        "followups": page_obj.object_list,
        "page_obj": page_obj,
        "stats": stats,
        "q": q,
        "status": status,
        "method": method,
        "date": date,
    }
    return render(request, "consultations/followup_list.html", context)


@login_required
def followup_detail(request, pk):
    followup = get_object_or_404(
        FollowUp.objects.select_related("appointment", "patient", "doctor").prefetch_related("attachments"),
        pk=pk
    )

    is_admin = _is_admin_user(request.user)
    is_patient_owner = followup.patient_id == request.user.id
    is_doctor_owner = getattr(followup.doctor, "user_id", None) == request.user.id

    if not (is_admin or is_patient_owner or is_doctor_owner):
        messages.error(request, "ليس لديك صلاحية للوصول إلى هذه المتابعة.")
        return redirect("consultations:followup_list")

    attachment_form = None
    if followup.is_followup_allowed:
        attachment_form = FollowUpAttachmentForm()

    appointment_exists = bool(getattr(followup, "appointment", None))

    context = {
        "followup": followup,
        "deadline": followup.followup_deadline,
        "is_followup_allowed": followup.is_followup_allowed,
        "requires_new_consultation": followup.requires_new_consultation,
        "days_remaining": followup.days_remaining_for_followup,
        "attachment_form": attachment_form,
        "appointment_exists": appointment_exists,
    }
    return render(request, "consultations/followup_detail.html", context)


@login_required
def followup_create(request):
    if request.method == "POST":
        appointment_id = request.POST.get("appointment")
        selected_appointment = None

        if appointment_id:
            try:
                selected_appointment = Appointment.objects.select_related(
                    "patient",
                    "doctor"
                ).get(pk=appointment_id)
            except Appointment.DoesNotExist:
                selected_appointment = None

        if not selected_appointment:
            messages.error(request, "الاستشارة الأصلية غير موجودة.")
            return redirect("consultations:followup_list")

        validation_response = _validate_followup_creation_access(request, selected_appointment)
        if validation_response:
            return validation_response

        form = FollowUpForm(
            request.POST,
            request_user=request.user,
            is_patient_edit=(selected_appointment.patient_id == request.user.id and not _is_admin_user(request.user))
        )
        attachment_form = FollowUpAttachmentForm(request.POST, request.FILES)

        if form.is_valid():
            followup = form.save()

            # إعادة فتح نفس الشات: المريض ينتظر والطبيب يبدأ من جديد
            if getattr(followup, "appointment", None):
                followup.appointment.reset_chat_session()

            # المرفق اختياري
            if request.FILES.get("file"):
                if attachment_form.is_valid():
                    attachment = attachment_form.save(commit=False)
                    attachment.followup = followup
                    attachment.uploaded_by = request.user
                    attachment.save()
                else:
                    messages.warning(
                        request,
                        "تم إنشاء المتابعة، لكن تعذر رفع المرفق. يرجى مراجعة نوع الملف أو حجمه."
                    )
                    return redirect("consultations:followup_detail", pk=followup.pk)

            messages.success(request, "تم إنشاء المتابعة الطبية بنجاح وإعادة تفعيل المحادثة.")
            return redirect("consultations:followup_detail", pk=followup.pk)

        messages.error(request, "تعذر حفظ المتابعة. يرجى مراجعة البيانات المدخلة.")

        context = {
            "form": form,
            "attachment_form": attachment_form,
            "page_title_dynamic": "إنشاء متابعة طبية",
            "selected_appointment": selected_appointment,
            "deadline": FollowUp.get_followup_deadline_for_appointment(selected_appointment),
            "is_followup_allowed": FollowUp.can_create_for_appointment(selected_appointment),
        }
        return render(request, "consultations/followup_form.html", context)

    appointment_id = request.GET.get("appointment")
    initial_data = {}
    selected_appointment = None
    deadline = None
    is_followup_allowed = None

    if appointment_id:
        selected_appointment = get_object_or_404(
            Appointment.objects.select_related("patient", "doctor"),
            pk=appointment_id
        )

        validation_response = _validate_followup_creation_access(request, selected_appointment)
        if validation_response:
            return validation_response

        is_followup_allowed = FollowUp.can_create_for_appointment(selected_appointment)
        deadline = FollowUp.get_followup_deadline_for_appointment(selected_appointment)

        # مهم:
        # لا نستخدم تاريخ الاستشارة الأصلية هنا، لأن الفورم يمنع تاريخاً أقدم من اليوم.
        # نبدأ بتاريخ اليوم ووقت الآن حتى لا تُرفض المتابعة من غير سبب.
        now_local = timezone.localtime()

        initial_data = {
            "appointment": selected_appointment,
            "patient": selected_appointment.patient,
            "doctor": selected_appointment.doctor,
            "method": selected_appointment.consultation_type,
            "status": "scheduled",
            "followup_date": timezone.localdate(),
            "followup_time": now_local.time().replace(second=0, microsecond=0),
        }

    form = FollowUpForm(
        initial=initial_data,
        request_user=request.user,
        is_patient_edit=True
    )
    attachment_form = FollowUpAttachmentForm()

    context = {
        "form": form,
        "attachment_form": attachment_form,
        "page_title_dynamic": "إنشاء متابعة طبية",
        "selected_appointment": selected_appointment,
        "deadline": deadline,
        "is_followup_allowed": is_followup_allowed,
    }
    return render(request, "consultations/followup_form.html", context)


@login_required
def followup_edit(request, pk):
    followup = get_object_or_404(
        FollowUp.objects.select_related("appointment", "patient", "doctor"),
        pk=pk
    )

    is_admin = _is_admin_user(request.user)

    # فقط المريض صاحب المتابعة أو الأدمن يقدر يعدل
    if not is_admin and request.user != followup.patient:
        messages.error(request, "ليس لديك صلاحية لتعديل بيانات هذه المتابعة.")
        return redirect("consultations:followup_detail", pk=followup.pk)

    if not getattr(followup, "appointment", None):
        messages.error(request, "الاستشارة الأصلية غير موجودة.")
        return redirect("consultations:followup_detail", pk=followup.pk)

    if followup.appointment.session_status != "completed":
        messages.error(request, "لا يمكن تعديل المتابعة قبل اكتمال الاستشارة الأصلية.")
        return redirect("consultations:followup_detail", pk=followup.pk)

    if not FollowUp.can_create_for_appointment(followup.appointment):
        messages.error(
            request,
            "انتهت مدة المتابعة المرتبطة بهذه الاستشارة، ويجب طلب استشارة جديدة."
        )
        return redirect("consultations:followup_detail", pk=followup.pk)

    if request.method == "POST":
        form = FollowUpForm(
            request.POST,
            instance=followup,
            request_user=request.user,
            is_patient_edit=not is_admin
        )

        # منع تعديل حقول الربط حتى من المريض
        for field_name in ["appointment", "patient", "doctor"]:
            if field_name in form.fields:
                form.fields[field_name].disabled = True

        if form.is_valid():
            updated_followup = form.save()
            messages.success(request, "تم تعديل المتابعة الطبية بنجاح.")
            return redirect("consultations:followup_detail", pk=updated_followup.pk)

        messages.error(request, "تعذر تعديل المتابعة. يرجى مراجعة البيانات المدخلة.")
    else:
        form = FollowUpForm(
            instance=followup,
            request_user=request.user,
            is_patient_edit=not is_admin
        )
        for field_name in ["appointment", "patient", "doctor"]:
            if field_name in form.fields:
                form.fields[field_name].disabled = True

    attachment_form = None
    if followup.is_followup_allowed:
        attachment_form = FollowUpAttachmentForm()

    context = {
        "form": form,
        "followup": followup,
        "attachment_form": attachment_form,
        "page_title_dynamic": "تعديل المتابعة الطبية",
        "selected_appointment": followup.appointment,
        "deadline": FollowUp.get_followup_deadline_for_appointment(followup.appointment),
        "is_followup_allowed": FollowUp.can_create_for_appointment(followup.appointment),
    }
    return render(request, "consultations/followup_form.html", context)


@login_required
def followup_create_from_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient", "doctor"),
        pk=appointment_id
    )

    validation_response = _validate_followup_creation_access(request, appointment)
    if validation_response:
        return validation_response

    return redirect(f"/consultations/followups/create/?appointment={appointment.pk}")


@login_required
def upload_followup_attachment(request, pk):
    followup = get_object_or_404(
        FollowUp.objects.select_related("appointment", "patient", "doctor"),
        pk=pk
    )

    is_admin = _is_admin_user(request.user)
    is_patient_owner = followup.patient_id == request.user.id
    is_doctor_owner = getattr(followup.doctor, "user_id", None) == request.user.id

    if not (is_admin or is_patient_owner or is_doctor_owner):
        messages.error(request, "ليس لديك صلاحية لرفع مرفق لهذه المتابعة.")
        return redirect("consultations:followup_detail", pk=followup.pk)

    if not followup.is_followup_allowed:
        messages.error(request, "انتهت صلاحية هذه المتابعة، ولا يمكن رفع مرفقات جديدة عليها.")
        return redirect("consultations:followup_detail", pk=followup.pk)

    if request.method == "POST":
        form = FollowUpAttachmentForm(
            request.POST,
            request.FILES,
            followup=followup,
            uploaded_by=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, "تم رفع المرفق الطبي بنجاح.")
        else:
            messages.error(request, "تعذر رفع المرفق. تأكد من نوع الملف وحجمه.")

    return redirect("consultations:followup_detail", pk=followup.pk)
