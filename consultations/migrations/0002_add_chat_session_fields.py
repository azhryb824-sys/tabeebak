from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="chat_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="chat_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
