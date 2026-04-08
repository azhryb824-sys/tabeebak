from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from appointments.models import Appointment
from doctors.models import Doctor
from appointments.forms import DoctorConsultationForm


@login_required
def dashboard_redirect_view(request):
    if request.user.is_staff or request.user.user_type == "admin":
        return redirect("/admin/")

    if request.user.user_type == "doctor":
        return redirect("doctor_dashboard")

    return redirect("patient_dashboard")


@login_required
def patient_dashboard(request):
    if request.user.user_type != "patient":
        return redirect("dashboard_redirect")

    appointments = Appointment.objects.select_related("doctor").filter(
        patient=request.user
    )

    total_appointments = appointments.count()
    pending_appointments = appointments.filter(status="pending").count()
    confirmed_appointments = appointments.filter(status="confirmed").count()
    cancelled_appointments = appointments.filter(status="cancelled").count()

    latest_appointments = appointments.order_by("-created_at")[:5]

    context = {
        "total_appointments": total_appointments,
        "pending_appointments": pending_appointments,
        "confirmed_appointments": confirmed_appointments,
        "cancelled_appointments": cancelled_appointments,
        "latest_appointments": latest_appointments,
    }
    return render(request, "dashboard/patient_dashboard.html", context)


@login_required
def doctor_dashboard(request):
    if request.user.user_type != "doctor":
        return redirect("dashboard_redirect")

    doctor = Doctor.objects.filter(user=request.user).first()
    if not doctor:
        return render(request, "dashboard/doctor_dashboard.html", {
            "doctor": None,
            "total_appointments": 0,
            "pending_appointments": 0,
            "confirmed_appointments": 0,
            "cancelled_appointments": 0,
            "latest_appointments": [],
        })

    appointments = Appointment.objects.select_related("patient").filter(doctor=doctor)

    total_appointments = appointments.count()
    pending_appointments = appointments.filter(status="pending").count()
    confirmed_appointments = appointments.filter(status="confirmed").count()
    cancelled_appointments = appointments.filter(status="cancelled").count()

    latest_appointments = appointments.order_by("-created_at")[:10]

    context = {
        "doctor": doctor,
        "total_appointments": total_appointments,
        "pending_appointments": pending_appointments,
        "confirmed_appointments": confirmed_appointments,
        "cancelled_appointments": cancelled_appointments,
        "latest_appointments": latest_appointments,
    }
    return render(request, "dashboard/doctor_dashboard.html", context)


@login_required
def doctor_update_appointment_status(request, appointment_id, status):
    if request.user.user_type != "doctor":
        return redirect("dashboard_redirect")

    if status not in ["confirmed", "cancelled"]:
        messages.error(request, "الحالة المطلوبة غير صحيحة.")
        return redirect("doctor_dashboard")

    doctor = get_object_or_404(Doctor, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)

    appointment.status = status
    appointment.save()

    if status == "confirmed":
        messages.success(request, "تم تأكيد الحجز بنجاح.")
    else:
        messages.success(request, "تم إلغاء الحجز بنجاح.")

    return redirect("doctor_dashboard")


@login_required
def doctor_appointment_detail(request, appointment_id):
    if request.user.user_type != "doctor":
        return redirect("dashboard_redirect")

    doctor = get_object_or_404(Doctor, user=request.user)
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient", "doctor"),
        id=appointment_id,
        doctor=doctor
    )

    return render(request, "dashboard/doctor_appointment_detail.html", {
        "doctor": doctor,
        "appointment": appointment,
    })
@login_required
def doctor_manage_consultation(request, appointment_id):
    if request.user.user_type != "doctor":
        return redirect("dashboard_redirect")

    doctor = get_object_or_404(Doctor, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)

    if request.method == "POST":
        form = DoctorConsultationForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات الاستشارة بنجاح.")
            return redirect("doctor_appointment_detail", appointment_id=appointment.id)
    else:
        form = DoctorConsultationForm(instance=appointment)

    return render(request, "dashboard/doctor_manage_consultation.html", {
        "doctor": doctor,
        "appointment": appointment,
        "form": form,
    })