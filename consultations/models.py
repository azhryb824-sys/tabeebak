from datetime import datetime, time, timedelta

from django.db import models
from django.utils import timezone

from appointments.models import Appointment
from doctors.models import Doctor
from django.conf import settings


class FollowUp(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "مجدولة"),
        ("completed", "مكتملة"),
        ("cancelled", "ملغية"),
    ]

    METHOD_CHOICES = [
        ("text", "متابعة كتابية"),
        ("voice", "متابعة صوتية"),
        ("video", "متابعة مرئية"),
    ]

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="followups",
        verbose_name="الاستشارة الأصلية"
    )

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followups",
        verbose_name="المريض"
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="followups",
        verbose_name="الطبيب"
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default="text",
        verbose_name="نوع المتابعة"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled",
        verbose_name="الحالة"
    )

    followup_date = models.DateField(
        verbose_name="تاريخ المتابعة"
    )

    followup_time = models.TimeField(
        verbose_name="وقت المتابعة"
    )

    patient_note = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظات المريض"
    )

    doctor_note = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظات الطبيب"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخر تحديث"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "متابعة طبية"
        verbose_name_plural = "المتابعات الطبية"

    def __str__(self):
        return f"متابعة #{self.id} - {self.appointment.full_name}"

    @property
    def appointment_datetime(self):
        """
        دمج تاريخ ووقت الاستشارة الأصلية.
        """
        if self.appointment.appointment_date and self.appointment.appointment_time:
            return datetime.combine(
                self.appointment.appointment_date,
                self.appointment.appointment_time
            )
        return None

    @property
    def appointment_datetime_aware(self):
        """
        تحويل وقت الاستشارة الأصلية إلى aware datetime للمقارنة الآمنة.
        """
        appointment_dt = self.appointment_datetime
        if not appointment_dt:
            return None

        if timezone.is_naive(appointment_dt):
            return timezone.make_aware(appointment_dt, timezone.get_current_timezone())
        return appointment_dt

    @property
    def followup_deadline(self):
        """
        آخر وقت مسموح فيه بإنشاء متابعة:
        بعد 14 يوم من وقت الاستشارة الأصلية.
        """
        appointment_dt = self.appointment_datetime_aware
        if not appointment_dt:
            return None
        return appointment_dt + timedelta(days=14)

    @property
    def is_followup_allowed(self):
        """
        هل المتابعة ما زالت مسموحة بناءً على شرط الـ 14 يوم؟
        """
        deadline = self.followup_deadline
        if not deadline:
            return False
        return timezone.now() <= deadline

    @property
    def days_remaining_for_followup(self):
        """
        عدد الأيام المتبقية للسماح بالمتابعة.
        لو انتهت المدة يرجع 0.
        """
        deadline = self.followup_deadline
        if not deadline:
            return 0

        remaining = deadline - timezone.now()
        if remaining.total_seconds() <= 0:
            return 0

        # نقرّبها للأعلى لو في كسور يوم
        return max(1, remaining.days if remaining.seconds == 0 else remaining.days + 1)

    @property
    def requires_new_consultation(self):
        """
        لو انتهت مهلة المتابعة، لازم استشارة جديدة.
        """
        return not self.is_followup_allowed

    @classmethod
    def can_create_for_appointment(cls, appointment):
        """
        دالة عامة تفحص هل يمكن إنشاء متابعة لهذا الموعد.
        """
        if not appointment:
            return False

        if not appointment.appointment_date or not appointment.appointment_time:
            return False

        appointment_dt = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        )

        if timezone.is_naive(appointment_dt):
            appointment_dt = timezone.make_aware(
                appointment_dt,
                timezone.get_current_timezone()
            )

        deadline = appointment_dt + timedelta(days=14)
        return timezone.now() <= deadline

    @classmethod
    def get_followup_deadline_for_appointment(cls, appointment):
        """
        إرجاع آخر وقت مسموح للمتابعة لموعد معين.
        """
        if not appointment:
            return None

        if not appointment.appointment_date or not appointment.appointment_time:
            return None

        appointment_dt = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        )

        if timezone.is_naive(appointment_dt):
            appointment_dt = timezone.make_aware(
                appointment_dt,
                timezone.get_current_timezone()
            )

        return appointment_dt + timedelta(days=14)

    def clean(self):
        """
        حماية إضافية على مستوى الموديل:
        - تأكيد تطابق الطبيب والمريض مع الاستشارة الأصلية
        - منع إنشاء متابعة بعد 14 يوم
        """
        from django.core.exceptions import ValidationError

        errors = {}

        if self.appointment:
            if self.patient and self.appointment.patient and self.patient != self.appointment.patient:
                errors["patient"] = "المريض المختار لا يطابق المريض الموجود في الاستشارة الأصلية."

            if self.doctor and self.appointment.doctor and self.doctor != self.appointment.doctor:
                errors["doctor"] = "الطبيب المختار لا يطابق الطبيب الموجود في الاستشارة الأصلية."

            if not self.__class__.can_create_for_appointment(self.appointment):
                errors["appointment"] = "انتهت مدة المتابعة لهذه الاستشارة، ويجب حجز استشارة جديدة."

            if self.followup_date:
                deadline = self.__class__.get_followup_deadline_for_appointment(self.appointment)
                if deadline and self.followup_date > deadline.date():
                    errors["followup_date"] = "تاريخ المتابعة خارج المدة المسموح بها، ويجب حجز استشارة جديدة."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """
        تشغيل clean قبل الحفظ لضمان تطبيق الشرط دائماً.
        """
        self.full_clean()
        super().save(*args, **kwargs)
