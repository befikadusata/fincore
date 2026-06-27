from django.db import models
from core.models import TenantScopedModel
from apps.notifications.constants import NotificationChannel, NotificationStatus


class Notification(TenantScopedModel):
    recipient = models.ForeignKey(
        'saas.User', on_delete=models.CASCADE, related_name='notifications'
    )
    event_type = models.CharField(max_length=100)
    channel = models.CharField(
        max_length=20, choices=NotificationChannel.choices, default=NotificationChannel.IN_APP
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    entity_type = models.CharField(max_length=100, blank=True, default='')
    entity_id = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(
        max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.SENT
    )
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'tenant', 'status']),
        ]
