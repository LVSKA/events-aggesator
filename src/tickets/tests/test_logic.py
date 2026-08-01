import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from events.models import Event, EventStatus, Place
from tickets import logic
from tickets.exceptions import (
    RegistrationClosed,
    SeatNotInPattern,
    TicketAlreadyCancelled,
    TicketNotFound,
)
from tickets.models import Ticket


def _make_place(seats_pattern="A1-10"):
    now = datetime.now(UTC)
    return Place.objects.create(
        id=uuid.uuid4(),
        name="Hall",
        city="Moscow",
        address="Lenina 1",
        seats_pattern=seats_pattern,
        changed_at=now,
        created_at=now,
    )


def _make_event(place, status=EventStatus.PUBLISHED, deadline=None):
    now = datetime.now(UTC)
    return Event.objects.create(
        id=uuid.uuid4(),
        name="Conference",
        place=place,
        event_time=now,
        registration_deadline=deadline or now + timedelta(days=1),
        status=status,
        number_of_visitors=0,
        changed_at=now,
        created_at=now,
        status_changed_at=now,
    )


@pytest.mark.django_db
def test_create_ticket_registers_with_provider_and_saves_locally():
    place = _make_place()
    event = _make_event(place)
    client = Mock()
    client.register.return_value = str(uuid.uuid4())

    ticket = logic.create_ticket(client, event.id, "Ivan", "Ivanov", "ivan@example.com", "A5")

    client.register.assert_called_once_with(
        str(event.id), "Ivan", "Ivanov", "ivan@example.com", "A5"
    )
    assert Ticket.objects.filter(ticket_id=ticket.ticket_id).exists()


@pytest.mark.django_db
def test_create_ticket_rejects_seat_outside_pattern():
    place = _make_place(seats_pattern="A1-10")
    event = _make_event(place)
    client = Mock()

    with pytest.raises(SeatNotInPattern):
        logic.create_ticket(client, event.id, "Ivan", "Ivanov", "ivan@example.com", "B1")

    client.register.assert_not_called()


@pytest.mark.django_db
def test_create_ticket_rejects_unpublished_event():
    place = _make_place()
    event = _make_event(place, status=EventStatus.NEW)
    client = Mock()

    with pytest.raises(RegistrationClosed):
        logic.create_ticket(client, event.id, "Ivan", "Ivanov", "ivan@example.com", "A5")


@pytest.mark.django_db
def test_create_ticket_rejects_after_deadline():
    place = _make_place()
    event = _make_event(place, deadline=datetime.now(UTC) - timedelta(days=1))
    client = Mock()

    with pytest.raises(RegistrationClosed):
        logic.create_ticket(client, event.id, "Ivan", "Ivanov", "ivan@example.com", "A5")


@pytest.mark.django_db
def test_create_ticket_for_same_seat_reuses_returned_ticket_id():
    # regression test for the documented quirk: the provider can hand back
    # the same ticket_id for a seat that was previously cancelled
    place = _make_place()
    event = _make_event(place)
    client = Mock()
    shared_ticket_id = str(uuid.uuid4())
    client.register.return_value = shared_ticket_id

    first = logic.create_ticket(client, event.id, "Ivan", "Ivanov", "ivan@example.com", "A5")
    logic.cancel_ticket(client, first.ticket_id)
    second = logic.create_ticket(client, event.id, "Petr", "Petrov", "petr@example.com", "A5")

    assert str(first.ticket_id) == str(second.ticket_id)
    assert not second.is_cancelled()


@pytest.mark.django_db
def test_cancel_ticket_calls_provider_and_marks_cancelled():
    place = _make_place()
    event = _make_event(place)
    ticket = Ticket.objects.create(
        ticket_id=uuid.uuid4(),
        event=event,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A5",
    )
    client = Mock()

    logic.cancel_ticket(client, ticket.ticket_id)

    client.unregister.assert_called_once_with(str(event.id), str(ticket.ticket_id))
    ticket.refresh_from_db()
    assert ticket.is_cancelled()


@pytest.mark.django_db
def test_cancel_ticket_raises_for_unknown_ticket():
    client = Mock()

    with pytest.raises(TicketNotFound):
        logic.cancel_ticket(client, uuid.uuid4())


@pytest.mark.django_db
def test_cancel_ticket_raises_if_already_cancelled():
    place = _make_place()
    event = _make_event(place)
    ticket = Ticket.objects.create(
        ticket_id=uuid.uuid4(),
        event=event,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A5",
        cancelled_at=datetime.now(UTC),
    )
    client = Mock()

    with pytest.raises(TicketAlreadyCancelled):
        logic.cancel_ticket(client, ticket.ticket_id)

