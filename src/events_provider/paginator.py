from __future__ import annotations

from collections.abc import Iterator

from events_provider.client import EventsProviderClient
from events_provider.schemas import RawEvent


class EventsPaginator:
    """Walks every page of GET /api/events/ for a given changed_at, hiding
    the provider's cursor-based pagination behind a plain iterator.

    Usage:
        for event in EventsPaginator(client, changed_at="2000-01-01"):
            save_event(event)
    """

    def __init__(self, client: EventsProviderClient, changed_at: str):
        self._client = client
        self._changed_at = changed_at

    def __iter__(self) -> Iterator[RawEvent]:
        cursor = None
        while True:
            page = self._client.get_events(self._changed_at, cursor=cursor)
            yield from page.results

            if page.next_cursor is None:
                return
            cursor = page.next_cursor
