from django.db import models


class SyncStatus(models.TextChoices):
    IDLE = "idle", "Idle"
    RUNNING = "running", "Running"
    FAILED = "failed", "Failed"


class SyncMetadata(models.Model):
    """Single-row table tracking the state of event synchronization.

    Always accessed by a fixed pk=1, see sync.logic.synchronize_events.
    """

    last_changed_at = models.DateTimeField(null=True, blank=True)
    last_sync_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=SyncStatus.choices, default=SyncStatus.IDLE)
    last_error = models.TextField(blank=True, default="")

    def __str__(self):
        return f"sync metadata ({self.status})"
