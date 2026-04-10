from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "__first__"),
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
