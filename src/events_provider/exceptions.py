class EventsProviderError(Exception):
    """Base exception for all errors returned by the Events Provider API."""


class AuthenticationError(EventsProviderError):
    """Raised on 401 responses (missing or invalid API key)."""


class EventNotFound(EventsProviderError):
    """Raised on 404 responses for an unknown event."""


class EventNotPublished(EventsProviderError):
    """Raised when an operation requires a published event, but it isn't one.

    The provider currently returns a 500 with an HTML body for this case
    instead of a proper 4xx/JSON error, so the client translates it here
    into something the rest of the codebase can actually catch.
    """


class SeatAlreadyTaken(EventsProviderError):
    """Raised when trying to register for a seat that's already sold."""


class RateLimited(EventsProviderError):
    """Raised on 429 responses."""
