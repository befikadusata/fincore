from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'tenant',
            'actor_id',
            'actor_type',
            'action',
            'entity_type',
            'entity_id',
            'changes',
            'ip_address',
            'user_agent',
            'created_at',
        ]
        read_only_fields = fields
