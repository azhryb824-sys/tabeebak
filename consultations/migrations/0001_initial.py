from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("appointments", "__first__"),
        ("doctors", "__first__"),
    ]

    operations = [
        migrations.CreateModel(
            name="FollowUp",
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
                    "method",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("text", "متابعة كتابية"),
                            ("voice", "متابعة صوتية"),
                            ("video", "متابعة مرئية"),
                        ],
                        default="text",
                        verbose_name="نوع المتابعة",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("scheduled", "مجدولة"),
                            ("completed", "مكتملة"),
                            ("cancelled", "ملغية"),
                        ],
                        default="scheduled",
                        verbose_name="الحالة",
                    ),
                ),
                (
                    "followup_date",
                    models.DateField(verbose_name="تاريخ المتابعة"),
                ),
                (
                    "followup_time",
                    models.TimeField(verbose_name="وقت المتابعة"),
                ),
                (
                    "patient_note",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="ملاحظات المريض",
                    ),
                ),
                (
                    "doctor_note",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="ملاحظات الطبيب",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="تاريخ الإنشاء",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="آخر تحديث",
                    ),
                ),
                (
                    "appointment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="followups",
                        to="appointments.appointment",
                        verbose_name="الاستشارة الأصلية",
                    ),
                ),
                (
                    "doctor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="followups",
                        to="doctors.doctor",
                        verbose_name="الطبيب",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="followups",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="المريض",
                    ),
                ),
            ],
            options={
                "verbose_name": "متابعة طبية",
                "verbose_name_plural": "المتابعات الطبية",
                "ordering": ["-created_at"],
            },
        ),
    ]
