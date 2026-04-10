from django.contrib import admin
from .models import FollowUp


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "appointment",
        "patient",
        "doctor",
        "method",
        "status",
        "followup_date",
        "followup_time",
        "created_at",
    )
    list_filter = (
        "status",
        "method",
        "followup_date",
        "created_at",
    )
    search_fields = (
        "appointment__full_name",
        "appointment__phone",
        "appointment__email",
        "patient__username",
        "patient__first_name",
        "patient__last_name",
        "doctor__name",
        "patient_note",
        "doctor_note",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "appointment",
        "patient",
        "doctor",
    )
    ordering = ("-created_at",)

    fieldsets = (
        ("بيانات الربط", {
            "fields": (
                "appointment",
                "patient",
                "doctor",
            )
        }),
        ("بيانات المتابعة", {
            "fields": (
                "method",
                "status",
                "followup_date",
                "followup_time",
            )
        }),
        ("الملاحظات", {
            "fields": (
                "patient_note",
                "doctor_note",
            )
        }),
        ("معلومات النظام", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )
