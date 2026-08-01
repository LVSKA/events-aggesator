from django.conf import settings
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from events import logic
from events.serializers import EventDetailSerializer, EventListSerializer
from events_provider.client import EventsProviderClient
from events_provider.exceptions import EventNotPublished


class EventListView(ListAPIView):
    serializer_class = EventListSerializer

    def get_queryset(self):
        date_from = self.request.query_params.get("date_from")
        return logic.list_events(date_from=date_from)


class EventDetailView(APIView):
    def get(self, request, event_id):
        try:
            event = logic.get_event(event_id)
        except logic.EventNotFound as exc:
            raise NotFound("Event not found") from exc

        return Response(EventDetailSerializer(event).data)


class EventSeatsView(APIView):
    def get(self, request, event_id):
        client = EventsProviderClient(
            base_url=settings.EVENTS_PROVIDER_BASE_URL,
            api_key=settings.EVENTS_PROVIDER_API_KEY,
        )
        try:
            seats = logic.get_available_seats(event_id, client)
        except logic.EventNotFound as exc:
            raise NotFound("Event not found") from exc
        except EventNotPublished as exc:
            return Response({"detail": str(exc)}, status=409)

        return Response({"event_id": str(event_id), "available_seats": seats})
