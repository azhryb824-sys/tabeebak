from django import forms
from .models import Appointment
from .models import Appointment, AppointmentAttachment
from .models import DoctorReview

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            "full_name",
            "phone",
            "email",
            "consultation_type",
            "appointment_date",
            "appointment_time",
            "notes",
            "age",
            "gender",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "اكتب الاسم الكامل",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "05xxxxxxxx",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "name@example.com",
            }),
            "consultation_type": forms.Select(attrs={
                "class": "form-select",
            }),
            "appointment_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "appointment_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "اكتب وصفاً مختصراً للأعراض أو سبب الحجز",
            }),
            "age": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "مثال: 32",
            }),
            "gender": forms.Select(attrs={
                "class": "form-select",
            }),
        }
        labels = {
            "full_name": "الاسم الكامل",
            "phone": "رقم الجوال",
            "email": "البريد الإلكتروني",
            "consultation_type": "نوع الاستشارة",
            "appointment_date": "تاريخ الموعد",
            "appointment_time": "وقت الموعد",
            "notes": "سبب الاستشارة",
            "age": "العمر",
            "gender": "الجنس",
        }
class DoctorConsultationForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            "doctor_notes",
            "diagnosis",
            "treatment_plan",
            "session_status",
        ]
        widgets = {
            "doctor_notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "اكتب ملاحظات الطبيب",
            }),
            "diagnosis": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "اكتب التشخيص",
            }),
            "treatment_plan": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "اكتب الخطة العلاجية أو التوصيات",
            }),
            "session_status": forms.Select(attrs={
                "class": "form-select",
            }),
        }
        labels = {
            "doctor_notes": "ملاحظات الطبيب",
            "diagnosis": "التشخيص",
            "treatment_plan": "الخطة العلاجية",
            "session_status": "حالة الجلسة",
        }
class AttachmentUploadForm(forms.ModelForm):
    class Meta:
        model = AppointmentAttachment
        fields = ["title", "file"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثال: تحليل دم / تقرير أشعة",
            }),
            "file": forms.ClearableFileInput(attrs={
                "class": "form-control",
            }),
        }
        labels = {
            "title": "عنوان الملف",
            "file": "اختر الملف",
        }
class DoctorReviewForm(forms.ModelForm):
    class Meta:
        model = DoctorReview
        fields = ["rating", "comment"]

        widgets = {
            "rating": forms.RadioSelect(
                choices=[(1, "⭐"), (2, "⭐⭐"), (3, "⭐⭐⭐"), (4, "⭐⭐⭐⭐"), (5, "⭐⭐⭐⭐⭐")]
            ),
            "comment": forms.Textarea(attrs={
                "rows": 4,
                "class": "form-control",
                "placeholder": "اكتب رأيك في الطبيب..."
            }),
        }