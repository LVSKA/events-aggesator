import logging

from django.utils import timezone

from events.models import Event, Place
from events_provider.client import EventsProviderClient
from events_provider.paginator import EventsPaginator
from events_provider.schemas import RawEvent
from sync.models import SyncMetadata, SyncStatus

logger = logging.getLogger(__name__)

FIRST_SYNC_CHANGED_AT = "2000-01-01"


def _save_event(raw_event: RawEvent) -> None:
    place, _ = Place.objects.update_or_create(
        id=raw_event.place.id,
        defaults={
            "name": raw_event.place.name,
            "city": raw_event.place.city,
            "address": raw_event.place.address,
            "seats_pattern": raw_event.place.seats_pattern,
            "changed_at": raw_event.place.changed_at,
            "created_at": raw_event.place.created_at,
        },
    )

    Event.objects.update_or_create(
        id=raw_event.id,
        defaults={
            "name": raw_event.name,
            "place": place,
            "event_time": raw_event.event_time,
            "registration_deadline": raw_event.registration_deadline,
            "status": raw_event.status,
            "number_of_visitors": raw_event.number_of_visitors,
            "changed_at": raw_event.changed_at,
            "created_at": raw_event.created_at,
            "status_changed_at": raw_event.status_changed_at,
        },
    )


def synchronize_events(client: EventsProviderClient) -> None:
    metadata, _ = SyncMetadata.objects.get_or_create(pk=1)
    changed_at = (
        metadata.last_changed_at.date().isoformat()
        if metadata.last_changed_at
        else FIRST_SYNC_CHANGED_AT
    )

    metadata.status = SyncStatus.RUNNING
    metadata.save(update_fields=["status"])

    latest_changed_at = metadata.last_changed_at
    processed = 0

    try:
        for raw_event in EventsPaginator(client, changed_at=changed_at):
            _save_event(raw_event)
            processed += 1
            if latest_changed_at is None or raw_event.changed_at > latest_changed_at:
                latest_changed_at = raw_event.changed_at
    except Exception as exc:
        metadata.status = SyncStatus.FAILED
        metadata.last_error = str(exc)
        metadata.save(update_fields=["status", "last_error"])
        logger.exception("Event synchronization failed after processing %s events", processed)
        raise

    metadata.status = SyncStatus.IDLE
    metadata.last_error = ""
    metadata.last_sync_time = timezone.now()
    if latest_changed_at is not None:
        metadata.last_changed_at = latest_changed_at
    metadata.save(update_fields=["status", "last_error", "last_sync_time", "last_changed_at"])

    logger.info("Event synchronization finished, processed %s events", processed)
