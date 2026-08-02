from django.urls import path

from tickets.views import TicketCreateView, TicketDeleteView

urlpatterns = [
    path("tickets", TicketCreateView.as_view(), name="ticket-create"),
    path("tickets/<uuid:ticket_id>/", TicketDeleteView.as_view(), name="ticket-delete"),
]
