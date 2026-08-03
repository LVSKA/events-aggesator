from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from events_provider.client import EventsProviderClient
from events_provider.exceptions import SeatAlreadyTaken
from tickets import logic
from tickets.exceptions import (
    RegistrationClosed,
    SeatNotInPattern,
    TicketAlreadyCancelled,
    TicketNotFound,
)
from tickets.serializers import TicketCreateSerializer, TicketSerializer


def _build_client() -> EventsProviderClient:
    return EventsProviderClient(
        base_url=settings.EVENTS_PROVIDER_BASE_URL,
        api_key=settings.EVENTS_PROVIDER_API_KEY,
    )


class TicketCreateView(APIView):
    def post(self, request):
        serializer = TicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            ticket = logic.create_ticket(_build_client(), **data)
        except TicketNotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except (RegistrationClosed, SeatNotInPattern) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except SeatAlreadyTaken as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

class TicketDeleteView(APIView):
    def delete(self, request, ticket_id):
        try:
            logic.cancel_ticket(_build_client(), ticket_id)
        except TicketNotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except TicketAlreadyCancelled as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True})
