from django.contrib import admin

from events.models import Event, Place

admin.site.register(Place)
admin.site.register(Event)
