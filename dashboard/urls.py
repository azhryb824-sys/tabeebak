from django.urls import path
from .views import (
    dashboard_redirect_view,
    patient_dashboard,
    doctor_dashboard,
    doctor_update_appointment_status,
    doctor_appointment_detail,
    doctor_manage_consultation,
)

urlpatterns = [
    path("", dashboard_redirect_view, name="dashboard_redirect"),
    path("patient/", patient_dashboard, name="patient_dashboard"),
    path("doctor/", doctor_dashboard, name="doctor_dashboard"),
    path(
        "doctor/appointment/<int:appointment_id>/",
        doctor_appointment_detail,
        name="doctor_appointment_detail",
    ),
    path(
        "doctor/appointment/<int:appointment_id>/manage/",
        doctor_manage_consultation,
        name="doctor_manage_consultation",
    ),
    path(
        "doctor/appointment/<int:appointment_id>/<str:status>/",
        doctor_update_appointment_status,
        name="doctor_update_appointment_status",
    ),
]