from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("doctors", "__first__"),
    ]

    operations = [
        migrations.CreateModel(
            name="Appointment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "full_name",
                    models.CharField(max_length=255),
                ),
                (
                    "phone",
                    models.CharField(max_length=20),
                ),
                (
                    "email",
                    models.EmailField(blank=True, max_length=254, null=True),
                ),
                (
                    "consultation_type",
                    models.CharField(
                        choices=[
                            ("text", "استشارة كتابية"),
                            ("voice", "استشارة صوتية"),
                            ("video", "استشارة مرئية"),
                        ],
                        default="text",
                        max_length=20,
                    ),
                ),
                (
                    "appointment_date",
                    models.DateField(),
                ),
                (
                    "appointment_time",
                    models.TimeField(),
                ),
                (
                    "notes",
                    models.TextField(blank=True, null=True),
                ),
                (
                    "age",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "gender",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("male", "ذكر"),
                            ("female", "أنثى"),
                        ],
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "قيد المراجعة"),
                            ("confirmed", "مؤكد"),
                            ("cancelled", "ملغي"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "session_status",
                    models.CharField(
                        choices=[
                            ("not_started", "لم تبدأ"),
                            ("in_progress", "جارية"),
                            ("completed", "مكتملة"),
                        ],
                        default="not_started",
                        max_length=20,
                    ),
                ),
                (
                    "doctor_notes",
                    models.TextField(blank=True, null=True),
                ),
                (
                    "diagnosis",
                    models.TextField(blank=True, null=True),
                ),
                (
                    "treatment_plan",
                    models.TextField(blank=True, null=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "chat_started_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "chat_expires_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "doctor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="appointments",
                        to="doctors.doctor",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="appointments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AppointmentAttachment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "file",
                    models.FileField(upload_to="appointments/attachments/"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "appointment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="appointments.appointment",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="uploaded_appointment_attachments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AppointmentMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "content",
                    models.TextField(),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "appointment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="appointments.appointment",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="appointment_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="DoctorReview",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "rating",
                    models.PositiveSmallIntegerField(),
                ),
                (
                    "comment",
                    models.TextField(blank=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "appointment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review",
                        to="appointments.appointment",
                    ),
                ),
                (
                    "doctor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="doctors.doctor",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="doctor_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
