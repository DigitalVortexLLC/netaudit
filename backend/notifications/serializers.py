from rest_framework import serializers

from .models import WebhookHeader, WebhookProvider


class WebhookHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookHeader
        fields = ["id", "key", "value"]


class WebhookProviderSerializer(serializers.ModelSerializer):
    headers = WebhookHeaderSerializer(many=True, required=False)

    class Meta:
        model = WebhookProvider
        fields = [
            "id",
            "name",
            "url",
            "enabled",
            "trigger_mode",
            "headers",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        headers_data = validated_data.pop("headers", [])
        provider = WebhookProvider.objects.create(**validated_data)
        for header_data in headers_data:
            WebhookHeader.objects.create(provider=provider, **header_data)
        return provider

    def update(self, instance, validated_data):
        headers_data = validated_data.pop("headers", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if headers_data is not None:
            instance.headers.all().delete()
            for header_data in headers_data:
                WebhookHeader.objects.create(provider=instance, **header_data)

        return instance
