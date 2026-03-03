from rest_framework import serializers

from .models import SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ["default_api_endpoint", "slack_webhook_url", "public_registration_enabled"]
