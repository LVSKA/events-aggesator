from django.urls import path

from sync.views import SyncTriggerView

urlpatterns = [
    path("sync/trigger/", SyncTriggerView.as_view(), name="sync-trigger"),
    path("sync/trigger", SyncTriggerView.as_view(), name="sync-trigger-no-slash"),
]
