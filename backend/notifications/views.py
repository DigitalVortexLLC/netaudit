import logging
from datetime import datetime, timezone

import requests as http_requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove

from .models import WebhookProvider
from .serializers import WebhookProviderSerializer

logger = logging.getLogger(__name__)


class WebhookProviderViewSet(viewsets.ModelViewSet):
    queryset = WebhookProvider.objects.prefetch_related("headers").all()
    serializer_class = WebhookProviderSerializer
    search_fields = ["name", "url"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        provider = self.get_object()
        headers = {h.key: h.value for h in provider.headers.all()}
        headers["Content-Type"] = "application/json"

        payload = {
            "event": "webhook.test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "This is a test webhook from NetAudit.",
            "provider_name": provider.name,
        }

        try:
            response = http_requests.post(
                provider.url, json=payload, headers=headers, timeout=10,
            )
            return Response({
                "success": True,
                "status_code": response.status_code,
            })
        except Exception as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
