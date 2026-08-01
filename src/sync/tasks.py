from django.conf import settings

from core.celery import app
from events_provider.client import EventsProviderClient
from sync.logic import synchronize_events


@app.task(name="sync.tasks.synchronize_events_task")
def synchronize_events_task():
    client = EventsProviderClient(
        base_url=settings.EVENTS_PROVIDER_BASE_URL,
        api_key=settings.EVENTS_PROVIDER_API_KEY,
    )
    synchronize_events(client)
