from rest_framework import serializers

from audits.models import AuditComment, AuditRun, AuditSchedule, RuleResult, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "created_at"]
        read_only_fields = ["created_at"]


class AuditCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source="author.username", read_only=True, default="Deleted user"
    )

    class Meta:
        model = AuditComment
        fields = [
            "id",
            "audit_run",
            "author",
            "author_name",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author", "audit_run", "created_at", "updated_at"]


class RuleResultSerializer(serializers.ModelSerializer):
    rule_name = serializers.SerializerMethodField()

    class Meta:
        model = RuleResult
        fields = "__all__"

    def get_rule_name(self, obj):
        if obj.simple_rule:
            return obj.simple_rule.name
        if obj.custom_rule:
            return obj.custom_rule.name
        return None


class AuditRunListSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = AuditRun
        fields = [
            "id",
            "device",
            "device_name",
            "status",
            "trigger",
            "summary",
            "started_at",
            "completed_at",
            "created_at",
            "tags",
        ]


class AuditRunDetailSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    results = RuleResultSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comments = AuditCommentSerializer(many=True, read_only=True)

    class Meta:
        model = AuditRun
        fields = [
            "id",
            "device",
            "device_name",
            "status",
            "trigger",
            "summary",
            "started_at",
            "completed_at",
            "created_at",
            "results",
            "error_message",
            "config_fetched_at",
            "tags",
            "comments",
        ]


class AuditRunCreateSerializer(serializers.Serializer):
    device = serializers.IntegerField()

    def validate_device(self, value):
        from devices.models import Device

        try:
            return Device.objects.get(pk=value)
        except Device.DoesNotExist:
            raise serializers.ValidationError("Device not found.")


class AuditScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditSchedule
        fields = "__all__"
        read_only_fields = ["django_q_schedule_id"]
