from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SyncMetadata",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("last_changed_at", models.DateTimeField(blank=True, null=True)),
                ("last_sync_time", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("idle", "Idle"), ("running", "Running"), ("failed", "Failed")],
                        default="idle",
                        max_length=16,
                    ),
                ),
                ("last_error", models.TextField(blank=True, default="")),
            ],
        ),
    ]
