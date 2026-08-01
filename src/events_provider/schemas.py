from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawPlace:
    id: str
    name: str
    city: str
    address: str
    seats_pattern: str
    changed_at: datetime
    created_at: datetime


@dataclass
class RawEvent:
    id: str
    name: str
    place: RawPlace
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int
    changed_at: datetime
    created_at: datetime
    status_changed_at: datetime


@dataclass
class EventsPage:
    results: list[RawEvent]
    next_cursor: str | None
