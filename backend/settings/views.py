from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from audits.notifications import send_test_slack_notification

from .models import SiteSettings
from .serializers import SiteSettingsSerializer


@api_view(["GET", "PUT", "PATCH"])
def site_settings_view(request):
    settings = SiteSettings.load()
    if request.method == "GET":
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data)
    serializer = SiteSettingsSerializer(
        settings, data=request.data, partial=request.method == "PATCH"
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def test_slack_view(request):
    webhook_url = request.data.get("webhook_url", "").strip()
    if not webhook_url:
        return Response(
            {"error": "webhook_url is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    success = send_test_slack_notification(webhook_url)
    if success:
        return Response({"success": True})
    return Response(
        {"success": False, "error": "Failed to send test message"},
        status=status.HTTP_502_BAD_GATEWAY,
    )
