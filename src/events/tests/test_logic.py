import uuid
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from django.core.cache import cache

from events import logic
from events.models import Event, EventStatus, Place
from events_provider.exceptions import EventNotPublished


def _make_place():
    now = datetime.now(UTC)
    return Place.objects.create(
        id=uuid.uuid4(),
        name="Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern="A1-10",
        changed_at=now,
        created_at=now,
    )


def _make_event(place, status=EventStatus.PUBLISHED):
    now = datetime.now(UTC)
    return Event.objects.create(
        id=uuid.uuid4(),
        name="Conference",
        place=place,
        event_time=now,
        registration_deadline=now,
        status=status,
        number_of_visitors=0,
        changed_at=now,
        created_at=now,
        status_changed_at=now,
    )


@pytest.mark.django_db
def test_get_event_returns_existing_event():
    place = _make_place()
    event = _make_event(place)

    result = logic.get_event(event.id)

    assert result.id == event.id


@pytest.mark.django_db
def test_get_event_raises_not_found_for_unknown_id():
    with pytest.raises(logic.EventNotFound):
        logic.get_event(uuid.uuid4())


@pytest.mark.django_db
def test_get_available_seats_rejects_unpublished_event():
    place = _make_place()
    event = _make_event(place, status=EventStatus.NEW)

    with pytest.raises(EventNotPublished):
        logic.get_available_seats(event.id, client=None)


@pytest.mark.django_db
def test_get_available_seats_uses_cache():
    cache.clear()
    place = _make_place()
    event = _make_event(place)

    client = Mock()
    client.get_seats.return_value = ["A1", "A2"]

    first = logic.get_available_seats(event.id, client)
    second = logic.get_available_seats(event.id, client)

    assert first == ["A1", "A2"]
    assert second == ["A1", "A2"]
    client.get_seats.assert_called_once()


@pytest.mark.django_db
def test_list_events_filters_by_date_from():
    place = _make_place()
    _make_event(place)

    results = list(logic.list_events(date_from="2000-01-01"))

    assert len(results) == 1


@pytest.mark.django_db
def test_list_events_excludes_events_before_date_from():
    place = _make_place()
    event = _make_event(place)
    event.event_time = datetime(2020, 1, 1, tzinfo=UTC)
    event.save(update_fields=["event_time"])

    results = list(logic.list_events(date_from="2025-01-01"))

    assert len(results) == 0
