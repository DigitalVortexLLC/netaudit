from rest_framework import serializers

from config_sources.models import SshConfigSource
from config_sources.serializers import ConfigSourceField

from .models import Device, DeviceGroup, DeviceHeader

_UNSET = object()


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
    effective_api_endpoint = serializers.CharField(read_only=True)
    config_source = ConfigSourceField(required=False, allow_null=True)
    last_fetched_config = serializers.CharField(read_only=True)
    config_fetched_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "hostname",
            "api_endpoint",
            "effective_api_endpoint",
            "enabled",
            "headers",
            "groups",
            "config_source",
            "last_fetched_config",
            "config_fetched_at",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        headers_data = validated_data.pop("headers", [])
        groups_data = validated_data.pop("groups", [])
        config_source_data = validated_data.pop("config_source", _UNSET)
        device = Device.objects.create(**validated_data)
        for header_data in headers_data:
            DeviceHeader.objects.create(device=device, **header_data)
        if groups_data:
            device.groups.set(groups_data)
        if config_source_data is not _UNSET and config_source_data is not None:
            _handle_config_source(device, config_source_data)
        return device

    def update(self, instance, validated_data):
        headers_data = validated_data.pop("headers", None)
        groups_data = validated_data.pop("groups", None)
        config_source_data = validated_data.pop("config_source", _UNSET)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if headers_data is not None:
            instance.headers.all().delete()
            for header_data in headers_data:
                DeviceHeader.objects.create(device=instance, **header_data)

        if groups_data is not None:
            instance.groups.set(groups_data)

        if config_source_data is not _UNSET:
            _handle_config_source(instance, config_source_data)

        return instance


def _handle_config_source(instance, config_source_data):
    """Create, replace, or remove the config source for a device.

    - If config_source_data is None, remove the existing source.
    - If config_source_data has source_type="ssh", create a new SshConfigSource.
    - Old source is deleted before creating a new one.
    """
    # Delete old config source if it exists
    old_source = instance.config_source
    if old_source is not None:
        instance.config_source = None
        instance.save(update_fields=["config_source"])
        # Delete the child (SshConfigSource) and base (ConfigSource)
        if old_source.source_type == "ssh":
            try:
                old_source.sshconfigsource.delete()
            except SshConfigSource.DoesNotExist:
                old_source.delete()
        else:
            old_source.delete()

    # If data is None, we just remove the source
    if config_source_data is None:
        return

    # Create the new source
    source_type = config_source_data.pop("source_type", "ssh")
    if source_type == "ssh":
        ssh_source = SshConfigSource.objects.create(
            source_type="ssh",
            **config_source_data,
        )
        instance.config_source = ssh_source
        instance.save(update_fields=["config_source"])
