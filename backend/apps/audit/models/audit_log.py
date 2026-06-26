from django.db import models

from apps.audit.constants import AuditAction, ActorType
from core.models import BaseModel


class AuditLog(BaseModel):
    tenant = models.ForeignKey(
        'saas.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name='audit_logs',
    )
    actor_id = models.UUIDField(null=True, blank=True, db_index=True)
    actor_type = models.CharField(max_length=20, choices=ActorType.choices, default=ActorType.USER)
    action = models.CharField(max_length=30, choices=AuditAction.choices, db_index=True)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=100, blank=True, db_index=True)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['tenant', 'action']),
            models.Index(fields=['actor_id', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("AuditLog entries are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditLog entries are immutable and cannot be deleted.")

    def __str__(self):
        return f'{self.action}:{self.entity_type}/{self.entity_id}'
