from django.urls import path
from . import views

urlpatterns = [
    # 📋 قائمة المواعيد
    path("", views.appointment_list, name="appointment_list"),

    # 📄 تفاصيل الموعد
    path("<int:appointment_id>/", views.appointment_detail, name="appointment_detail"),

    # 📎 رفع مرفق
    path("<int:appointment_id>/upload/", views.upload_appointment_attachment, name="upload_appointment_attachment"),

    # 💬 الشات
    path("<int:appointment_id>/chat/", views.appointment_chat, name="appointment_chat"),

    # 📝 إنشاء حجز
    path("book/<int:doctor_id>/", views.booking_create, name="booking_create"),

    # ✅ نجاح الحجز
    path("success/<int:appointment_id>/", views.booking_success, name="booking_success"),

    # ⭐ تقييم الطبيب
    path(
        "<int:appointment_id>/review/",
        views.submit_doctor_review,
        name="submit_doctor_review"
    ),
]
