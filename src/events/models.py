from django.db import models


class EventStatus(models.TextChoices):
    NEW = "new", "New"
    PUBLISHED = "published", "Published"


class Place(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    seats_pattern = models.CharField(max_length=255)

    # timestamps as reported by the provider, not our own bookkeeping
    changed_at = models.DateTimeField()
    created_at = models.DateTimeField()

    def __str__(self):
        return f"{self.name} ({self.city})"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="events")

    event_time = models.DateTimeField(db_index=True)
    registration_deadline = models.DateTimeField()
    # not restricted to EventStatus choices only - the provider docs mention
    # more statuses may show up later, and sync shouldn't break on them
    status = models.CharField(max_length=32)
    number_of_visitors = models.PositiveIntegerField(default=0)

    changed_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField()
    status_changed_at = models.DateTimeField()

    class Meta:
        ordering = ["event_time"]

    def __str__(self):
        return self.name

    def is_published(self) -> bool:
        return self.status == EventStatus.PUBLISHED
