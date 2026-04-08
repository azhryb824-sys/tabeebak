from django.contrib import admin
from django.utils.html import format_html
from .models import Appointment


@admin.action(description="تأكيد الحجوزات المحددة")
def confirm_appointments(modeladmin, request, queryset):
    queryset.update(status="confirmed")


@admin.action(description="إلغاء الحجوزات المحددة")
def cancel_appointments(modeladmin, request, queryset):
    queryset.update(status="cancelled")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "patient",
        "doctor",
        "appointment_date",
        "appointment_time",
        "consultation_type",
        "colored_status",
        "created_at",
    )

    list_filter = (
        "status",
        "consultation_type",
        "appointment_date",
        "doctor",
    )

    search_fields = (
        "full_name",
        "phone",
        "email",
        "patient__username",
        "patient__first_name",
        "patient__last_name",
        "doctor__name",
        "doctor__specialization",
    )

    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    actions = [confirm_appointments, cancel_appointments]

    def colored_status(self, obj):
        if obj.status == "pending":
            color = "orange"
            label = "قيد المراجعة"
        elif obj.status == "confirmed":
            color = "green"
            label = "مؤكد"
        elif obj.status == "cancelled":
            color = "red"
            label = "ملغي"
        else:
            color = "gray"
            label = obj.status

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label
        )

    colored_status.short_description = "الحالة"