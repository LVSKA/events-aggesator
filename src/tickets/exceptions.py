class TicketError(Exception):
    """Base exception for ticket-related business errors."""


class TicketNotFound(TicketError):
    pass


class TicketAlreadyCancelled(TicketError):
    pass


class RegistrationClosed(TicketError):
    """Raised when the event isn't published or the deadline has passed."""


class SeatNotInPattern(TicketError):
    """Raised when the requested seat doesn't match the place's seats_pattern."""
