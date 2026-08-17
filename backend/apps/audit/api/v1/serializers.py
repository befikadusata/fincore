from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogListSerializer(serializers.ListSerializer):
    """Resolves every actor label for the page in one query.

    actor_id is a plain UUID column rather than a FK, so there is no
    select_related to lean on and a per-row lookup would be N+1.
    """

    def to_representation(self, data):
        rows = list(data)
        actor_ids = {row.actor_id for row in rows if row.actor_id}
        self.child.actor_names = _actor_names(actor_ids)
        return super().to_representation(rows)


def _actor_names(actor_ids):
    if not actor_ids:
        return {}
    from apps.saas.models import User

    users = User.objects.filter(id__in=actor_ids).only('id', 'email')
    return {user.id: user.email for user in users}


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        list_serializer_class = AuditLogListSerializer
        fields = [
            'id',
            'tenant',
            'actor_id',
            'actor_name',
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

    def get_actor_name(self, obj):
        """Email, not first/last name: those are EncryptedCharFields, and the
        email is the stable identifier an auditor traces actions by."""
        if not obj.actor_id:
            # Non-user actors carry no actor_id — label them by actor_type so
            # scheduled jobs are attributable rather than blank.
            return obj.get_actor_type_display()

        cached = getattr(self, 'actor_names', None)
        if cached is not None and obj.actor_id in cached:
            return cached[obj.actor_id]

        from apps.saas.models import User

        user = User.objects.filter(id=obj.actor_id).only('email').first()
        return user.email if user else None
