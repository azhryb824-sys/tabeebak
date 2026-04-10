from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from appointments.models import Appointment
from .forms import FollowUpForm
from .models import FollowUp


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

    paginator = Paginator(followups_qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    stats = {
        "total": FollowUp.objects.count(),
        "scheduled": FollowUp.objects.filter(status="scheduled").count(),
        "completed": FollowUp.objects.filter(status="completed").count(),
        "cancelled": FollowUp.objects.filter(status="cancelled").count(),
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


def followup_detail(request, pk):
    followup = get_object_or_404(
        FollowUp.objects.select_related("appointment", "patient", "doctor"),
        pk=pk
    )

    context = {
        "followup": followup,
        "deadline": followup.followup_deadline,
        "is_followup_allowed": followup.is_followup_allowed,
        "requires_new_consultation": followup.requires_new_consultation,
        "days_remaining": followup.days_remaining_for_followup,
    }
    return render(request, "consultations/followup_detail.html", context)


def followup_create(request):
    if request.method == "POST":
        form = FollowUpForm(request.POST)

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

        if selected_appointment and not FollowUp.can_create_for_appointment(selected_appointment):
            messages.error(
                request,
                "انتهت مدة المتابعة لهذه الاستشارة، ولا يمكن إنشاء متابعة إلا بعد حجز استشارة جديدة."
            )
            return redirect("consultations:followup_list")

        if form.is_valid():
            followup = form.save()
            messages.success(request, "تم إنشاء المتابعة الطبية بنجاح.")
            return redirect("consultations:followup_detail", pk=followup.pk)

        messages.error(request, "تعذر حفظ المتابعة. يرجى مراجعة البيانات المدخلة.")

        context = {
            "form": form,
            "page_title_dynamic": "إنشاء متابعة طبية",
            "selected_appointment": selected_appointment,
            "deadline": FollowUp.get_followup_deadline_for_appointment(selected_appointment) if selected_appointment else None,
            "is_followup_allowed": FollowUp.can_create_for_appointment(selected_appointment) if selected_appointment else None,
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

        is_followup_allowed = FollowUp.can_create_for_appointment(selected_appointment)
        deadline = FollowUp.get_followup_deadline_for_appointment(selected_appointment)

        if not is_followup_allowed:
            messages.error(
                request,
                "انتهت مدة المتابعة لهذه الاستشارة، ولا يمكن إنشاء متابعة إلا بعد حجز استشارة جديدة."
            )
            return redirect("consultations:followup_list")

        initial_data = {
            "appointment": selected_appointment,
            "patient": selected_appointment.patient,
            "doctor": selected_appointment.doctor,
            "method": selected_appointment.consultation_type,
        }

    form = FollowUpForm(initial=initial_data)

    context = {
        "form": form,
        "page_title_dynamic": "إنشاء متابعة طبية",
        "selected_appointment": selected_appointment,
        "deadline": deadline,
        "is_followup_allowed": is_followup_allowed,
    }
    return render(request, "consultations/followup_form.html", context)


def followup_edit(request, pk):
    followup = get_object_or_404(
        FollowUp.objects.select_related("appointment", "patient", "doctor"),
        pk=pk
    )

    if not FollowUp.can_create_for_appointment(followup.appointment):
        messages.error(
            request,
            "انتهت مدة المتابعة المرتبطة بهذه الاستشارة، ويجب حجز استشارة جديدة."
        )
        return redirect("consultations:followup_detail", pk=followup.pk)

    if request.method == "POST":
        form = FollowUpForm(request.POST, instance=followup)

        if form.is_valid():
            updated_followup = form.save()
            messages.success(request, "تم تعديل المتابعة الطبية بنجاح.")
            return redirect("consultations:followup_detail", pk=updated_followup.pk)

        messages.error(request, "تعذر تعديل المتابعة. يرجى مراجعة البيانات المدخلة.")
    else:
        form = FollowUpForm(instance=followup)

    context = {
        "form": form,
        "followup": followup,
        "page_title_dynamic": "تعديل المتابعة الطبية",
        "selected_appointment": followup.appointment,
        "deadline": FollowUp.get_followup_deadline_for_appointment(followup.appointment),
        "is_followup_allowed": FollowUp.can_create_for_appointment(followup.appointment),
    }
    return render(request, "consultations/followup_form.html", context)


def followup_create_from_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient", "doctor"),
        pk=appointment_id
    )

    if not FollowUp.can_create_for_appointment(appointment):
        messages.error(
            request,
            "انتهت مدة المتابعة لهذه الاستشارة، ولا يمكن إنشاء متابعة إلا بعد حجز استشارة جديدة."
        )
        return redirect("appointments:doctor_appointment_detail", pk=appointment.pk)

    return redirect(f"/consultations/followups/create/?appointment={appointment.pk}")
