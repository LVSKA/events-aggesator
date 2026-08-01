import uuid
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from events.models import Event, Place
from events_provider.schemas import EventsPage, RawEvent, RawPlace
from sync import logic
from sync.models import SyncMetadata, SyncStatus


def _raw_event(event_id=None, place_id=None, changed_at=None):
    event_id = event_id or str(uuid.uuid4())
    place_id = place_id or str(uuid.uuid4())
    changed_at = changed_at or datetime(2026, 1, 1, tzinfo=UTC)

    place = RawPlace(
        id=place_id,
        name="Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern="A1-10",
        changed_at=changed_at,
        created_at=changed_at,
    )
    return RawEvent(
        id=event_id,
        name="Conference",
        place=place,
        event_time=changed_at,
        registration_deadline=changed_at,
        status="published",
        number_of_visitors=0,
        changed_at=changed_at,
        created_at=changed_at,
        status_changed_at=changed_at,
    )


@pytest.mark.django_db
def test_first_sync_uses_default_changed_at():
    client = Mock()
    client.get_events.return_value = EventsPage(results=[], next_cursor=None)

    logic.synchronize_events(client)

    client.get_events.assert_called_once_with(logic.FIRST_SYNC_CHANGED_AT, cursor=None)


@pytest.mark.django_db
def test_sync_saves_events_and_places():
    event_id = str(uuid.uuid4())
    place_id = str(uuid.uuid4())
    client = Mock()
    client.get_events.return_value = EventsPage(
        results=[_raw_event(event_id=event_id, place_id=place_id)], next_cursor=None
    )

    logic.synchronize_events(client)

    assert Event.objects.filter(id=event_id).exists()
    assert Place.objects.filter(id=place_id).exists()


@pytest.mark.django_db
def test_sync_follows_pagination_across_pages():
    client = Mock()
    client.get_events.side_effect = [
        EventsPage(results=[_raw_event()], next_cursor="page-2"),
        EventsPage(results=[_raw_event(), _raw_event()], next_cursor=None),
    ]

    logic.synchronize_events(client)

    assert Event.objects.count() == 3
    assert client.get_events.call_count == 2


@pytest.mark.django_db
def test_sync_updates_metadata_on_success():
    changed_at = datetime(2026, 5, 1, tzinfo=UTC)
    client = Mock()
    client.get_events.return_value = EventsPage(
        results=[_raw_event(changed_at=changed_at)], next_cursor=None
    )

    logic.synchronize_events(client)

    metadata = SyncMetadata.objects.get(pk=1)
    assert metadata.status == SyncStatus.IDLE
    assert metadata.last_changed_at == changed_at
    assert metadata.last_sync_time is not None


@pytest.mark.django_db
def test_sync_marks_failed_status_on_error():
    client = Mock()
    client.get_events.side_effect = RuntimeError("provider is down")

    with pytest.raises(RuntimeError):
        logic.synchronize_events(client)

    metadata = SyncMetadata.objects.get(pk=1)
    assert metadata.status == SyncStatus.FAILED
    assert "provider is down" in metadata.last_error


@pytest.mark.django_db
def test_second_sync_uses_last_changed_at():
    SyncMetadata.objects.create(
        pk=1,
        last_changed_at=datetime(2026, 3, 1, tzinfo=UTC),
        status=SyncStatus.IDLE,
    )
    client = Mock()
    client.get_events.return_value = EventsPage(results=[], next_cursor=None)

    logic.synchronize_events(client)

    client.get_events.assert_called_once_with("2026-03-01", cursor=None)
