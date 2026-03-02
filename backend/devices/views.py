import requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove
from audits import tasks as audit_tasks

from .models import Device, DeviceGroup
from .serializers import DeviceGroupSerializer, DeviceSerializer


class DeviceGroupViewSet(viewsets.ModelViewSet):
    queryset = DeviceGroup.objects.prefetch_related("devices").all()
    serializer_class = DeviceGroupSerializer
    search_fields = ["name", "description"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    @action(detail=True, methods=["post"])
    def run_audit(self, request, pk=None):
        group = self.get_object()
        devices = group.devices.filter(enabled=True)
        for device in devices:
            audit_tasks.enqueue_audit(device.id, trigger="manual")
        return Response({
            "audits_started": devices.count(),
            "group": group.name,
        })


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.prefetch_related("headers").all()
    serializer_class = DeviceSerializer
    filterset_fields = ["enabled"]
    search_fields = ["name", "hostname"]
    ordering_fields = ["name", "created_at"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        device = self.get_object()
        endpoint = device.effective_api_endpoint
        if not endpoint:
            return Response(
                {"success": False, "error": "No API endpoint configured and no default endpoint is set."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        headers = {h.key: h.value for h in device.headers.all()}
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
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

    @action(detail=True, methods=["get"])
    def fetch_config(self, request, pk=None):
        device = self.get_object()
        endpoint = device.effective_api_endpoint
        if not endpoint:
            return Response(
                {"error": "No API endpoint configured and no default endpoint is set."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        headers = {h.key: h.value for h in device.headers.all()}
        try:
            response = requests.get(endpoint, headers=headers, timeout=30)
            response.raise_for_status()
            return Response({"config": response.text})
        except requests.RequestException as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
