from rest_framework import serializers

from .models import Device, DeviceGroup, DeviceHeader


class DeviceHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceHeader
        fields = ["id", "key", "value"]


class DeviceGroupSerializer(serializers.ModelSerializer):
    device_count = serializers.IntegerField(source="devices.count", read_only=True)
    devices = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Device.objects.all(), required=False,
    )

    class Meta:
        model = DeviceGroup
        fields = [
            "id",
            "name",
            "description",
            "devices",
            "device_count",
            "created_at",
            "updated_at",
        ]


class DeviceSerializer(serializers.ModelSerializer):
    headers = DeviceHeaderSerializer(many=True, required=False)
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=DeviceGroup.objects.all(), required=False,
    )

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "hostname",
            "api_endpoint",
            "enabled",
            "headers",
            "groups",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        headers_data = validated_data.pop("headers", [])
        groups_data = validated_data.pop("groups", [])
        device = Device.objects.create(**validated_data)
        for header_data in headers_data:
            DeviceHeader.objects.create(device=device, **header_data)
        if groups_data:
            device.groups.set(groups_data)
        return device

    def update(self, instance, validated_data):
        headers_data = validated_data.pop("headers", None)
        groups_data = validated_data.pop("groups", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if headers_data is not None:
            instance.headers.all().delete()
            for header_data in headers_data:
                DeviceHeader.objects.create(device=instance, **header_data)

        if groups_data is not None:
            instance.groups.set(groups_data)

        return instance
