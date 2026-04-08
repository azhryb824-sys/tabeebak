from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ("patient", "مريض"),
        ("doctor", "طبيب"),
        ("admin", "إدارة"),
    ]

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default="patient"
    )
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username