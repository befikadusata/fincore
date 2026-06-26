from django.db import models

from apps.events.constants import EventStatus
from core.models import TenantScopedModel


class DomainEvent(TenantScopedModel):
    event_type = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    # Redis Stream message ID recorded after successful publish
    stream_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'events_domain_event'
        indexes = [
            models.Index(fields=['event_type', 'status']),
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f'{self.event_type}:{self.entity_id} [{self.status}]'
