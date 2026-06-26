from rest_framework import serializers

from apps.events.models import DomainEvent, EventSubscription


class DomainEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainEvent
        fields = [
            'id', 'event_type', 'entity_type', 'entity_id',
            'payload', 'status', 'retry_count', 'error_message',
            'processed_at', 'created_at',
        ]
        read_only_fields = fields


class EventSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSubscription
        fields = ['id', 'event_type', 'handler_path', 'is_active', 'created_at']
