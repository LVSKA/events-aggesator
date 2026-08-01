import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from events.models import Event, EventStatus, Place


@pytest.fixture
def api_client():
    return APIClient()


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
def test_event_list_returns_events(api_client):
    place = _make_place()
    _make_event(place)

    response = api_client.get("/api/events/")

    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_event_list_respects_page_size(api_client):
    place = _make_place()
    for _ in range(3):
        _make_event(place)

    response = api_client.get("/api/events/", {"page_size": 2})

    assert response.status_code == 200
    assert response.data["count"] == 3
    assert len(response.data["results"]) == 2


@pytest.mark.django_db
def test_event_detail_returns_event(api_client):
    place = _make_place()
    event = _make_event(place)

    response = api_client.get(f"/api/events/{event.id}/")

    assert response.status_code == 200
    assert response.data["id"] == str(event.id)
    assert response.data["place"]["seats_pattern"] == "A1-10"


@pytest.mark.django_db
def test_event_detail_returns_404_for_unknown_event(api_client):
    response = api_client.get(f"/api/events/{uuid.uuid4()}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_event_seats_calls_provider_client(api_client):
    place = _make_place()
    event = _make_event(place)

    with patch("events.views.EventsProviderClient") as mock_client_cls:
        mock_client_cls.return_value.get_seats.return_value = ["A1", "A2"]

        response = api_client.get(f"/api/events/{event.id}/seats/")

    assert response.status_code == 200
    assert response.data["available_seats"] == ["A1", "A2"]


@pytest.mark.django_db
def test_event_seats_returns_conflict_for_unpublished_event(api_client):
    place = _make_place()
    event = _make_event(place, status=EventStatus.NEW)

    response = api_client.get(f"/api/events/{event.id}/seats/")

    assert response.status_code == 409
