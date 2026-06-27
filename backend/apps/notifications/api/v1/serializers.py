from rest_framework import serializers
from apps.notifications.models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'event_type', 'channel', 'title', 'body',
            'entity_type', 'entity_id', 'status', 'read_at',
            'metadata', 'created_at',
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id', 'event_type', 'in_app_enabled', 'email_enabled', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
