from django.db import models


class Doctor(models.Model):
    user = models.OneToOneField(
        "accounts.User",  # ✅ تم التعديل هنا
        on_delete=models.CASCADE,
        related_name="doctor_profile",
        blank=True,
        null=True
    )
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)
    experience_years = models.IntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    rating = models.FloatField(default=5.0)
    bio = models.TextField()
    image = models.ImageField(upload_to="doctors/", blank=True, null=True)

    def __str__(self):
        return self.name
