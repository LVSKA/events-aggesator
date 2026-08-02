from django.urls import path

from tickets.views import TicketCreateView, TicketDeleteView

urlpatterns = [
    path("tickets/", TicketCreateView.as_view(), name="ticket-create"),
    path("tickets", TicketCreateView.as_view(), name="ticket-create-no-slash"),
    path("tickets/<uuid:ticket_id>/", TicketDeleteView.as_view(), name="ticket-delete"),
    path("tickets/<uuid:ticket_id>", TicketDeleteView.as_view(), name="ticket-delete-no-slash"),
]
