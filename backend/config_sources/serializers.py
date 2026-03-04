from rest_framework import serializers

from .models import NetmikoDeviceType, SshConfigSource


class NetmikoDeviceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetmikoDeviceType
        fields = [
            "id",
            "name",
            "driver",
            "default_command",
            "extra_commands",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class SshConfigSourceSerializer(serializers.ModelSerializer):
    source_type = serializers.CharField(default="ssh")

    class Meta:
        model = SshConfigSource
        fields = [
            "source_type",
            "netmiko_device_type",
            "hostname",
            "port",
            "username",
            "password",
            "ssh_key",
            "command_override",
            "extra_commands",
            "prompt_overrides",
            "timeout",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "ssh_key": {"write_only": True, "required": False},
            "hostname": {"required": False},
            "port": {"required": False},
            "command_override": {"required": False},
            "extra_commands": {"required": False},
            "prompt_overrides": {"required": False},
            "timeout": {"required": False},
        }


class ConfigSourceField(serializers.Field):
    """Polymorphic serializer field for config sources."""

    def to_representation(self, value):
        if value is None:
            return None
        if value.source_type == "ssh":
            ssh = value.sshconfigsource
            return {
                "source_type": "ssh",
                "netmiko_device_type": ssh.netmiko_device_type_id,
                "hostname": ssh.hostname,
                "port": ssh.port,
                "username": ssh.username,
                "command_override": ssh.command_override,
                "extra_commands": ssh.extra_commands,
                "prompt_overrides": ssh.prompt_overrides,
                "timeout": ssh.timeout,
            }
        return {"source_type": value.source_type}

    def to_internal_value(self, data):
        if data is None:
            return None
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected a dict or null.")
        source_type = data.get("source_type")
        if source_type == "ssh":
            serializer = SshConfigSourceSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            return serializer.validated_data
        raise serializers.ValidationError(
            f"Unsupported source_type: {source_type}"
        )
