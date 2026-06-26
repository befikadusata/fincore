from django.db import models

from core.models import BaseModel


class EventSubscription(BaseModel):
    """DB-backed registry mapping event types to handler callables."""

    event_type = models.CharField(max_length=100, db_index=True)
    # Dotted Python import path to the handler function, e.g. 'apps.notifications.handlers.on_loan_approved'
    handler_path = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'events_subscription'
        constraints = [
            models.UniqueConstraint(fields=['event_type', 'handler_path'], name='uq_event_subscription'),
        ]

    def __str__(self):
        return f'{self.event_type} → {self.handler_path}'
