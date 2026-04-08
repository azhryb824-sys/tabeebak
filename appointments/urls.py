from django.urls import path
from django.urls import path
from .views import (
    booking_create,
    booking_success,
    appointment_list,
    appointment_detail,
    upload_appointment_attachment,
    appointment_chat,  # ← هذا هو المهم
)
from appointments import views

urlpatterns = [
    path("", appointment_list, name="appointment_list"),
    path("<int:appointment_id>/", appointment_detail, name="appointment_detail"),
    path("<int:appointment_id>/upload/", upload_appointment_attachment, name="upload_appointment_attachment"),
    path("book/<int:doctor_id>/", booking_create, name="booking_create"),
    path("success/<int:appointment_id>/", booking_success, name="booking_success"),
    path("<int:appointment_id>/chat/", appointment_chat, name="appointment_chat"),
    path(
    "appointments/<int:appointment_id>/review/",views.submit_doctor_review,
    
    name="submit_doctor_review"
),
]