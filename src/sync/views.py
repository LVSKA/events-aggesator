from rest_framework.response import Response
from rest_framework.views import APIView

from sync.tasks import synchronize_events_task


class SyncTriggerView(APIView):
    def post(self, request):
        synchronize_events_task.delay()
        return Response({"status": "triggered"})
