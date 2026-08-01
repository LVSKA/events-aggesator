from django.urls import path

from events.views import EventDetailView, EventListView, EventSeatsView

urlpatterns = [
    path("events/", EventListView.as_view(), name="event-list"),
    path("events/<uuid:event_id>/", EventDetailView.as_view(), name="event-detail"),
    path("events/<uuid:event_id>/seats/", EventSeatsView.as_view(), name="event-seats"),
]
