from django.db import models
from core.models import TenantScopedModel


class NotificationPreference(TenantScopedModel):
    user = models.ForeignKey(
        'saas.User', on_delete=models.CASCADE, related_name='notification_preferences'
    )
    event_type = models.CharField(max_length=100)
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'notifications_preference'
        unique_together = [('tenant', 'user', 'event_type')]
        ordering = ['event_type']
