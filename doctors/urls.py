from django.urls import path
from .views import doctor_list, doctor_detail

urlpatterns = [
    path("", doctor_list, name="doctor_list"),

    # ✅ صفحة تفاصيل الطبيب (المسار الصحيح)
    path("<int:doctor_id>/", doctor_detail, name="doctor_detail"),
]