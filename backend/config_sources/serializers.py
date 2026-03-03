from rest_framework import serializers

from .models import NetmikoDeviceType


class NetmikoDeviceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetmikoDeviceType
        fields = [
            "id",
            "name",
            "driver",
            "default_command",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
