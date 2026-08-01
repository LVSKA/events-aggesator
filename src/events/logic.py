from django.core.cache import cache

from events.models import Event, EventStatus
from events_provider.client import EventsProviderClient
from events_provider.exceptions import EventNotPublished

SEATS_CACHE_TTL = 30  # seconds, per assignment requirement


class EventNotFound(Exception):
    pass


def list_events(date_from=None):
    queryset = Event.objects.select_related("place")
    if date_from:
        queryset = queryset.filter(event_time__date__gte=date_from)
    return queryset


def get_event(event_id) -> Event:
    try:
        return Event.objects.select_related("place").get(id=event_id)
    except Event.DoesNotExist as exc:
        raise EventNotFound(str(event_id)) from exc


def get_available_seats(event_id, client: EventsProviderClient) -> list[str]:
    event = get_event(event_id)

    if event.status != EventStatus.PUBLISHED:
        # fail fast on our side instead of letting the provider return its
        # broken 500-with-HTML response for unpublished events
        raise EventNotPublished(f"Event {event_id} is not published")

    cache_key = f"seats:{event_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    seats = client.get_seats(str(event.id))
    cache.set(cache_key, seats, timeout=SEATS_CACHE_TTL)
    return seats
