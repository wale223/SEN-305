from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("requests_app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicerequest",
            name="due_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="servicerequest",
            name="resolution_summary",
            field=models.TextField(blank=True),
        ),
        migrations.AddIndex(
            model_name="servicerequest",
            index=models.Index(fields=["status", "due_at"], name="req_status_due_idx"),
        ),
    ]
