import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Ticket",
            fields=[
                ("ticket_id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("first_name", models.CharField(max_length=255)),
                ("last_name", models.CharField(max_length=255)),
                ("email", models.EmailField(max_length=254)),
                ("seat", models.CharField(max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets",
                        to="events.event",
                    ),
                ),
            ],
        ),
    ]
