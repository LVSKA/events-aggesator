import re

from django.utils import timezone

from events.logic import EventNotFound, get_event
from events.models import EventStatus
from events_provider.client import EventsProviderClient
from tickets.exceptions import (
    RegistrationClosed,
    SeatNotInPattern,
    TicketAlreadyCancelled,
    TicketNotFound,
)
from tickets.models import Ticket

_SECTION_RE = re.compile(r"([A-Za-z])(\d+)-(\d+)")
_SEAT_RE = re.compile(r"([A-Za-z]+)(\d+)")


def _seat_exists_in_pattern(seat: str, seats_pattern: str) -> bool:
    match = _SEAT_RE.fullmatch(seat)
    if not match:
        return False

    section, number = match.group(1), int(match.group(2))
    for section_letter, start, end in _SECTION_RE.findall(seats_pattern):
        if section_letter == section and int(start) <= number <= int(end):
            return True
    return False


def create_ticket(
    client: EventsProviderClient, event_id, first_name, last_name, email, seat
) -> Ticket:
    try:
        event = get_event(event_id)
    except EventNotFound as exc:
        raise TicketNotFound(f"Event {event_id} not found") from exc

    if event.status != EventStatus.PUBLISHED:
        raise RegistrationClosed(f"Event {event_id} is not open for registration")

    if timezone.now() > event.registration_deadline:
        raise RegistrationClosed(f"Registration deadline for event {event_id} has passed")

    if not _seat_exists_in_pattern(seat, event.place.seats_pattern):
        raise SeatNotInPattern(f"Seat {seat} doesn't exist at {event.place.name}")

    ticket_id = client.register(str(event.id), first_name, last_name, email, seat)

    # ticket_id is tied to the seat on the provider's side: if a previous
    # occupant of this seat cancelled, a new registration for the same seat
    # can come back with the same ticket_id. update_or_create keeps that
    # idempotent instead of failing on a duplicate primary key.
    ticket, _ = Ticket.objects.update_or_create(
        ticket_id=ticket_id,
        defaults={
            "event": event,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "seat": seat,
            "cancelled_at": None,
        },
    )
    return ticket


def cancel_ticket(client: EventsProviderClient, ticket_id) -> None:
    try:
        ticket = Ticket.objects.select_related("event").get(ticket_id=ticket_id)
    except Ticket.DoesNotExist as exc:
        raise TicketNotFound(str(ticket_id)) from exc

    if ticket.is_cancelled():
        raise TicketAlreadyCancelled(str(ticket_id))

    client.unregister(str(ticket.event_id), str(ticket_id))

    ticket.cancelled_at = timezone.now()
    ticket.save(update_fields=["cancelled_at"])
