from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import FollowUp, FollowUpAttachment


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
        self.request_user = kwargs.pop("request_user", None)
        self.is_patient_edit = kwargs.pop("is_patient_edit", False)
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if field_name not in ["patient_note", "doctor_note"]:
                existing_class = field.widget.attrs.get("class", "")
                if "form-control" not in existing_class and "form-select" not in existing_class:
                    field.widget.attrs["class"] = "form-control"

        # في حالة إنشاء متابعة من المريض:
        # نخفي فعلياً منطقياً تعديل بعض الحقول من الواجهة
        if self.is_patient_edit:
            for field_name in ["appointment", "patient", "doctor"]:
                if field_name in self.fields:
                    self.fields[field_name].disabled = True

            # المريض غالباً لا يحتاج تغيير حالة المتابعة أو ملاحظات الطبيب
            if "status" in self.fields:
                self.fields["status"].disabled = True
            if "doctor_note" in self.fields:
                self.fields["doctor_note"].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        appointment = cleaned_data.get("appointment") or getattr(self.instance, "appointment", None)
        patient = cleaned_data.get("patient") or getattr(self.instance, "patient", None)
        doctor = cleaned_data.get("doctor") or getattr(self.instance, "doctor", None)
        followup_date = cleaned_data.get("followup_date")

        if not appointment:
            raise ValidationError("يجب اختيار الاستشارة الأصلية أولاً.")

        # لا يمكن إنشاء متابعة إلا بعد اكتمال الاستشارة الأصلية
        if appointment.session_status != "completed":
            raise ValidationError("لا يمكن إنشاء متابعة قبل اكتمال الاستشارة الأصلية.")

        # منع المتابعة بعد 14 يوم من الاستشارة
        if not FollowUp.can_create_for_appointment(appointment):
            raise ValidationError(
                "انتهت مدة المتابعة لهذه الاستشارة، ولا يمكن إنشاء متابعة إلا بعد طلب استشارة جديدة."
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
                "تاريخ المتابعة يتجاوز المهلة المسموح بها. يجب طلب استشارة جديدة."
            )

        # منع اختيار تاريخ متابعة أقدم من اليوم في الإنشاء الجديد
        if followup_date and not self.instance.pk:
            if followup_date < timezone.localdate():
                self.add_error("followup_date", "لا يمكن اختيار تاريخ متابعة سابق لليوم.")

        # لو كان المستخدم الحالي مريضاً، لازم يكون هو مريض الموعد نفسه
        if self.request_user and appointment.patient:
            is_admin = getattr(self.request_user, "user_type", "") == "admin" or self.request_user.is_staff
            if not is_admin and self.request_user == appointment.patient:
                if patient and patient != self.request_user:
                    self.add_error("patient", "لا يمكنك إنشاء متابعة لمريض آخر.")
            elif not is_admin and self.request_user != appointment.patient:
                raise ValidationError("المتابعة الطبية متاحة للمريض صاحب الاستشارة فقط.")

        return cleaned_data


class FollowUpAttachmentForm(forms.ModelForm):
    class Meta:
        model = FollowUpAttachment
        fields = ["title", "file"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "عنوان الملف (اختياري)"
            }),
            "file": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }
        labels = {
            "title": "عنوان الملف",
            "file": "المرفق الطبي",
        }

    def __init__(self, *args, **kwargs):
        self.followup = kwargs.pop("followup", None)
        self.uploaded_by = kwargs.pop("uploaded_by", None)
        super().__init__(*args, **kwargs)

    def clean_file(self):
        file = self.cleaned_data.get("file")

        if not file:
            raise ValidationError("يرجى اختيار ملف لرفعه.")

        allowed_extensions = [
            ".jpg", ".jpeg", ".png", ".gif", ".webp",
            ".pdf", ".doc", ".docx"
        ]

        lower_name = file.name.lower()
        if not any(lower_name.endswith(ext) for ext in allowed_extensions):
            raise ValidationError("نوع الملف غير مدعوم. ارفع صورة أو ملف PDF أو Word.")

        max_size_mb = 10
        if file.size > max_size_mb * 1024 * 1024:
            raise ValidationError("حجم الملف كبير جداً. الحد الأقصى 10 ميجابايت.")

        return file

    def clean(self):
        cleaned_data = super().clean()

        if self.followup and not self.followup.is_followup_allowed:
            raise ValidationError("انتهت صلاحية هذه المتابعة، ولا يمكن رفع مرفقات جديدة عليها.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.followup:
            instance.followup = self.followup

        if self.uploaded_by:
            instance.uploaded_by = self.uploaded_by

        if commit:
            instance.save()

        return instance
