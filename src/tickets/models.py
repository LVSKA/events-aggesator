from django.db import models

from events.models import Event


class Ticket(models.Model):
    ticket_id = models.UUIDField(primary_key=True, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")

    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    seat = models.CharField(max_length=32)

    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.seat} - {self.first_name} {self.last_name}"

    def is_cancelled(self) -> bool:
        return self.cancelled_at is not None
