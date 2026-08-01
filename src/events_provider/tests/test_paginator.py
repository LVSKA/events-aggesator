from unittest.mock import Mock

from events_provider.paginator import EventsPaginator
from events_provider.schemas import EventsPage, RawEvent, RawPlace


def _make_event(event_id: str) -> RawEvent:
    place = RawPlace(
        id="place-1",
        name="Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern="A1-10",
        changed_at=None,
        created_at=None,
    )
    return RawEvent(
        id=event_id,
        name="Event",
        place=place,
        event_time=None,
        registration_deadline=None,
        status="published",
        number_of_visitors=0,
        changed_at=None,
        created_at=None,
        status_changed_at=None,
    )


def test_paginator_iterates_over_all_pages():
    client = Mock()
    client.get_events.side_effect = [
        EventsPage(results=[_make_event("1"), _make_event("2")], next_cursor="page-2"),
        EventsPage(results=[_make_event("3")], next_cursor=None),
    ]

    events = list(EventsPaginator(client, changed_at="2000-01-01"))

    assert [event.id for event in events] == ["1", "2", "3"]
    assert client.get_events.call_count == 2


def test_paginator_passes_cursor_to_next_call():
    client = Mock()
    client.get_events.side_effect = [
        EventsPage(results=[_make_event("1")], next_cursor="cursor-a"),
        EventsPage(results=[_make_event("2")], next_cursor=None),
    ]

    list(EventsPaginator(client, changed_at="2000-01-01"))

    first_call, second_call = client.get_events.call_args_list
    assert first_call.kwargs["cursor"] is None
    assert second_call.kwargs["cursor"] == "cursor-a"


def test_paginator_stops_on_single_page():
    client = Mock()
    client.get_events.return_value = EventsPage(results=[_make_event("1")], next_cursor=None)

    events = list(EventsPaginator(client, changed_at="2000-01-01"))

    assert len(events) == 1
    assert client.get_events.call_count == 1


def test_paginator_can_be_iterated_twice():
    client = Mock()
    client.get_events.return_value = EventsPage(results=[_make_event("1")], next_cursor=None)

    paginator = EventsPaginator(client, changed_at="2000-01-01")

    assert len(list(paginator)) == 1
    assert len(list(paginator)) == 1
