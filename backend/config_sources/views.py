from rest_framework import viewsets

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove

from .models import NetmikoDeviceType
from .serializers import NetmikoDeviceTypeSerializer


class NetmikoDeviceTypeViewSet(viewsets.ModelViewSet):
    queryset = NetmikoDeviceType.objects.all()
    serializer_class = NetmikoDeviceTypeSerializer
    search_fields = ["name", "driver"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]
