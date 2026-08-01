from unittest.mock import Mock, patch

import pytest

from events_provider.client import EventsProviderClient
from events_provider.exceptions import (
    AuthenticationError,
    EventNotFound,
    EventNotPublished,
    SeatAlreadyTaken,
)


@pytest.fixture
def client():
    return EventsProviderClient(base_url="http://provider.test", api_key="secret")


def _mock_response(status_code=200, json_data=None, text=""):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text
    return response


@patch("events_provider.client.requests.request")
def test_get_events_parses_results_and_cursor(mock_request, client):
    mock_request.return_value = _mock_response(
        json_data={
            "next": "http://provider.test/api/events/?changed_at=2000-01-01&cursor=abc",
            "previous": None,
            "results": [
                {
                    "id": "event-1",
                    "name": "Conference",
                    "place": {
                        "id": "place-1",
                        "name": "Hall",
                        "city": "Moscow",
                        "address": "Lenina 1",
                        "seats_pattern": "A1-10",
                        "changed_at": "2025-01-01T03:00:00+03:00",
                        "created_at": "2025-01-01T03:00:00+03:00",
                    },
                    "event_time": "2026-01-11T17:00:00+03:00",
                    "registration_deadline": "2026-01-10T17:00:00+03:00",
                    "status": "published",
                    "number_of_visitors": 5,
                    "changed_at": "2026-01-04T22:28:35.325270+03:00",
                    "created_at": "2026-01-04T22:28:35.325302+03:00",
                    "status_changed_at": "2026-01-04T22:28:35.325386+03:00",
                }
            ],
        }
    )

    page = client.get_events(changed_at="2000-01-01")

    assert page.next_cursor == "abc"
    assert len(page.results) == 1
    assert page.results[0].id == "event-1"
    assert page.results[0].place.city == "Moscow"


@patch("events_provider.client.requests.request")
def test_get_events_uses_trailing_slash(mock_request, client):
    mock_request.return_value = _mock_response(json_data={"next": None, "results": []})

    client.get_events(changed_at="2000-01-01")

    url = mock_request.call_args.args[1]
    assert url.endswith("/api/events/")


@patch("events_provider.client.requests.request")
def test_get_events_passes_cursor_as_query_param(mock_request, client):
    mock_request.return_value = _mock_response(json_data={"next": None, "results": []})

    client.get_events(changed_at="2000-01-01", cursor="xyz")

    params = mock_request.call_args.kwargs["params"]
    assert params == {"changed_at": "2000-01-01", "cursor": "xyz"}


@patch("events_provider.client.requests.request")
def test_get_seats_returns_seat_list(mock_request, client):
    mock_request.return_value = _mock_response(json_data={"seats": ["A1", "A2"]})

    seats = client.get_seats("event-1")

    assert seats == ["A1", "A2"]


@patch("events_provider.client.requests.request")
def test_get_seats_on_unpublished_event_raises_event_not_published(mock_request, client):
    mock_request.return_value = _mock_response(
        status_code=500,
        text="UnexpectedEventStatus: Event is not published for registration.",
    )

    with pytest.raises(EventNotPublished):
        client.get_seats("event-1")


@patch("events_provider.client.requests.request")
def test_register_on_taken_seat_raises_seat_already_taken(mock_request, client):
    mock_request.return_value = _mock_response(
        status_code=400,
        text='["This ticket is not available (already sold)."]',
    )

    with pytest.raises(SeatAlreadyTaken):
        client.register("event-1", "Ivan", "Ivanov", "ivan@example.com", "A15")


@patch("events_provider.client.requests.request")
def test_register_returns_ticket_id(mock_request, client):
    mock_request.return_value = _mock_response(
        status_code=201, json_data={"ticket_id": "ticket-1"}
    )

    ticket_id = client.register("event-1", "Ivan", "Ivanov", "ivan@example.com", "A15")

    assert ticket_id == "ticket-1"


@patch("events_provider.client.requests.request")
def test_missing_event_raises_event_not_found(mock_request, client):
    mock_request.return_value = _mock_response(
        status_code=404, text='{"detail": "Event not found."}'
    )

    with pytest.raises(EventNotFound):
        client.get_seats("missing-event")


@patch("events_provider.client.requests.request")
def test_bad_api_key_raises_authentication_error(mock_request, client):
    mock_request.return_value = _mock_response(status_code=401, text='{"detail": "invalid key"}')

    with pytest.raises(AuthenticationError):
        client.get_seats("event-1")


@patch("events_provider.client.requests.request")
def test_unregister_sends_ticket_id_in_body(mock_request, client):
    mock_request.return_value = _mock_response(status_code=200, json_data={"success": True})

    client.unregister("event-1", "ticket-1")

    body = mock_request.call_args.kwargs["json"]
    assert body == {"ticket_id": "ticket-1"}
