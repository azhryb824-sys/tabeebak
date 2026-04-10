from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import FollowUp


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = [
            "appointment",
            "patient",
            "doctor",
            "method",
            "status",
            "followup_date",
            "followup_time",
            "patient_note",
            "doctor_note",
        ]
        widgets = {
            "appointment": forms.Select(attrs={
                "class": "form-select"
            }),
            "patient": forms.Select(attrs={
                "class": "form-select"
            }),
            "doctor": forms.Select(attrs={
                "class": "form-select"
            }),
            "method": forms.Select(attrs={
                "class": "form-select"
            }),
            "status": forms.Select(attrs={
                "class": "form-select"
            }),
            "followup_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "followup_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time"
            }),
            "patient_note": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "اكتب ملاحظات المريض هنا"
            }),
            "doctor_note": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "اكتب ملاحظات الطبيب هنا"
            }),
        }
        labels = {
            "appointment": "الاستشارة الأصلية",
            "patient": "المريض",
            "doctor": "الطبيب",
            "method": "نوع المتابعة",
            "status": "الحالة",
            "followup_date": "تاريخ المتابعة",
            "followup_time": "وقت المتابعة",
            "patient_note": "ملاحظات المريض",
            "doctor_note": "ملاحظات الطبيب",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if field_name not in ["patient_note", "doctor_note"]:
                existing_class = field.widget.attrs.get("class", "")
                if "form-control" not in existing_class and "form-select" not in existing_class:
                    field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()

        appointment = cleaned_data.get("appointment")
        patient = cleaned_data.get("patient")
        doctor = cleaned_data.get("doctor")
        followup_date = cleaned_data.get("followup_date")

        if not appointment:
            raise ValidationError("يجب اختيار الاستشارة الأصلية أولاً.")

        # منع المتابعة بعد 14 يوم من الاستشارة
        if not FollowUp.can_create_for_appointment(appointment):
            raise ValidationError(
                "انتهت مدة المتابعة لهذه الاستشارة، ولا يمكن إنشاء متابعة إلا بعد حجز استشارة جديدة."
            )

        # التأكد من تطابق المريض مع الاستشارة الأصلية
        if appointment.patient and patient and appointment.patient != patient:
            self.add_error("patient", "المريض المختار لا يطابق المريض الموجود في الاستشارة الأصلية.")

        # التأكد من تطابق الطبيب مع الاستشارة الأصلية
        if appointment.doctor and doctor and appointment.doctor != doctor:
            self.add_error("doctor", "الطبيب المختار لا يطابق الطبيب الموجود في الاستشارة الأصلية.")

        # منع تحديد تاريخ متابعة بعد انتهاء مهلة المتابعة
        deadline = FollowUp.get_followup_deadline_for_appointment(appointment)
        if deadline and followup_date and followup_date > deadline.date():
            self.add_error(
                "followup_date",
                "تاريخ المتابعة يتجاوز المهلة المسموح بها. يجب حجز استشارة جديدة."
            )

        # منع اختيار تاريخ متابعة أقدم من اليوم في الإنشاء الجديد
        if followup_date and not self.instance.pk:
            if followup_date < timezone.localdate():
                self.add_error("followup_date", "لا يمكن اختيار تاريخ متابعة سابق لليوم.")

        return cleaned_data
