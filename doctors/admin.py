from django.contrib import admin
from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "specialization",
        "experience_years",
        "price",
        "rating",
    )
    search_fields = ("name", "specialization", "user__username", "user__email")
    list_filter = ("specialization",)