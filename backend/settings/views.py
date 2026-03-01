from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

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
