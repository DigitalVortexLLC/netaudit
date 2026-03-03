from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "is_api_enabled", "is_active", "date_joined")
        read_only_fields = ("id", "username", "email", "date_joined")
