from django.db import models
from django.conf import settings
from doctors.models import Doctor


class Appointment(models.Model):
    CONSULTATION_TYPE_CHOICES = [
        ("text", "استشارة كتابية"),
        ("voice", "استشارة صوتية"),
        ("video", "استشارة مرئية"),
    ]

    GENDER_CHOICES = [
        ("male", "ذكر"),
        ("female", "أنثى"),
    ]

    STATUS_CHOICES = [
        ("pending", "قيد المراجعة"),
        ("confirmed", "مؤكد"),
        ("cancelled", "ملغي"),
    ]

    SESSION_STATUS_CHOICES = [
        ("not_started", "لم تبدأ"),
        ("in_progress", "جارية"),
        ("completed", "مكتملة"),
    ]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
        blank=True,
        null=True
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="appointments"
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    consultation_type = models.CharField(
        max_length=20,
        choices=CONSULTATION_TYPE_CHOICES,
        default="text"
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    notes = models.TextField(blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    session_status = models.CharField(
        max_length=20,
        choices=SESSION_STATUS_CHOICES,
        default="not_started"
    )
    doctor_notes = models.TextField(blank=True, null=True)
    diagnosis = models.TextField(blank=True, null=True)
    treatment_plan = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} - {self.doctor.name} - {self.appointment_date}"


class AppointmentAttachment(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(upload_to="appointments/attachments/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_appointment_attachments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or self.file.name.split("/")[-1]

    @property
    def filename(self):
        return self.file.name.split("/")[-1]
class AppointmentMessage(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointment_messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username} - {self.appointment.id}"
class DoctorReview(models.Model):
    appointment = models.OneToOneField(
        "Appointment",
        on_delete=models.CASCADE,
        related_name="review"
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_reviews"
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doctor} - {self.rating}/5"