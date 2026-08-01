import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Place",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("city", models.CharField(max_length=255)),
                ("address", models.CharField(max_length=255)),
                ("seats_pattern", models.CharField(max_length=255)),
                ("changed_at", models.DateTimeField()),
                ("created_at", models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name="Event",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("event_time", models.DateTimeField(db_index=True)),
                ("registration_deadline", models.DateTimeField()),
                ("status", models.CharField(max_length=32)),
                ("number_of_visitors", models.PositiveIntegerField(default=0)),
                ("changed_at", models.DateTimeField(db_index=True)),
                ("created_at", models.DateTimeField()),
                ("status_changed_at", models.DateTimeField()),
                (
                    "place",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="events.place",
                    ),
                ),
            ],
            options={"ordering": ["event_time"]},
        ),
    ]
