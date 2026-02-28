from rest_framework import serializers

from .models import Device, DeviceHeader


class DeviceHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceHeader
        fields = ["id", "key", "value"]


class DeviceSerializer(serializers.ModelSerializer):
    headers = DeviceHeaderSerializer(many=True, required=False)

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "hostname",
            "api_endpoint",
            "enabled",
            "headers",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        headers_data = validated_data.pop("headers", [])
        device = Device.objects.create(**validated_data)
        for header_data in headers_data:
            DeviceHeader.objects.create(device=device, **header_data)
        return device

    def update(self, instance, validated_data):
        headers_data = validated_data.pop("headers", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if headers_data is not None:
            instance.headers.all().delete()
            for header_data in headers_data:
                DeviceHeader.objects.create(device=instance, **header_data)

        return instance
