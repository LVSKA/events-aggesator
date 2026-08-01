from __future__ import annotations

from datetime import datetime
from urllib.parse import parse_qs, urlparse

import requests

from events_provider.exceptions import (
    AuthenticationError,
    EventNotFound,
    EventNotPublished,
    EventsProviderError,
    RateLimited,
    SeatAlreadyTaken,
)
from events_provider.schemas import EventsPage, RawEvent, RawPlace


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _parse_place(raw: dict) -> RawPlace:
    return RawPlace(
        id=raw["id"],
        name=raw["name"],
        city=raw["city"],
        address=raw["address"],
        seats_pattern=raw["seats_pattern"],
        changed_at=_parse_datetime(raw["changed_at"]),
        created_at=_parse_datetime(raw["created_at"]),
    )


def _parse_event(raw: dict) -> RawEvent:
    return RawEvent(
        id=raw["id"],
        name=raw["name"],
        place=_parse_place(raw["place"]),
        event_time=_parse_datetime(raw["event_time"]),
        registration_deadline=_parse_datetime(raw["registration_deadline"]),
        status=raw["status"],
        number_of_visitors=raw["number_of_visitors"],
        changed_at=_parse_datetime(raw["changed_at"]),
        created_at=_parse_datetime(raw["created_at"]),
        status_changed_at=_parse_datetime(raw["status_changed_at"]),
    )


def _extract_cursor(next_url: str | None) -> str | None:
    if not next_url:
        return None
    query = parse_qs(urlparse(next_url).query)
    values = query.get("cursor")
    return values[0] if values else None


class EventsProviderClient:
    """Thin wrapper around the Events Provider REST API.

    All HTTP calls to the external service live here and nowhere else in
    the project - everything else talks to this class, never to requests
    directly.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self._base_url = base_url.rstrip("/")
        self._headers = {"x-api-key": api_key}
        self._timeout = timeout

    def get_events(self, changed_at: str, cursor: str | None = None) -> EventsPage:
        params = {"changed_at": changed_at}
        if cursor:
            params["cursor"] = cursor

        response = self._request("GET", "/api/events/", params=params)
        payload = response.json()

        results = [_parse_event(raw) for raw in payload["results"]]
        next_cursor = _extract_cursor(payload.get("next"))
        return EventsPage(results=results, next_cursor=next_cursor)

    def get_seats(self, event_id: str) -> list[str]:
        response = self._request("GET", f"/api/events/{event_id}/seats/")
        return response.json()["seats"]

    def register(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str:
        body = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "seat": seat,
        }
        response = self._request("POST", f"/api/events/{event_id}/register/", json=body)
        return response.json()["ticket_id"]

    def unregister(self, event_id: str, ticket_id: str) -> None:
        self._request(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": ticket_id},
        )

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self._base_url}{path}"
        response = requests.request(
            method, url, headers=self._headers, timeout=self._timeout, **kwargs
        )
        self._raise_for_status(response)
        return response

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.status_code < 400:
            return

        if response.status_code == 401:
            raise AuthenticationError(response.text)
        if response.status_code == 404:
            raise EventNotFound(response.text)
        if response.status_code == 429:
            raise RateLimited(response.text)

        body = response.text.lower()

        if response.status_code == 500 and "not published" in body:
            raise EventNotPublished(response.text)

        if response.status_code == 400 and ("already sold" in body or "not available" in body):
            raise SeatAlreadyTaken(response.text)

        raise EventsProviderError(f"Unexpected response {response.status_code}: {response.text}")
