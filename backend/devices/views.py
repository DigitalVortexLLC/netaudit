import requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Device
from .serializers import DeviceSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.prefetch_related("headers").all()
    serializer_class = DeviceSerializer
    filterset_fields = ["enabled"]
    search_fields = ["name", "hostname"]
    ordering_fields = ["name", "created_at"]

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        device = self.get_object()
        headers = {h.key: h.value for h in device.headers.all()}
        try:
            response = requests.get(
                device.api_endpoint,
                headers=headers,
                timeout=10,
            )
            return Response(
                {
                    "success": True,
                    "status_code": response.status_code,
                    "content_length": len(response.content),
                }
            )
        except requests.RequestException as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
