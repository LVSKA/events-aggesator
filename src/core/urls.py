from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("healthcheck.urls")),
    path("api/", include("events.urls")),
    path("api/", include("tickets.urls")),
    path("api/", include("sync.urls")),
]
