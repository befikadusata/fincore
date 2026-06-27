import logging
from django.utils import timezone

from apps.notifications.constants import NotificationChannel, NotificationStatus
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services.channels.in_app import InAppChannel
from apps.notifications.services.channels.email import EmailChannel

logger = logging.getLogger(__name__)

_CHANNELS = {
    NotificationChannel.IN_APP: InAppChannel(),
    NotificationChannel.EMAIL: EmailChannel(),
}


class NotificationService:
    @staticmethod
    def notify(
        user,
        tenant,
        event_type: str,
        title: str,
        body: str,
        entity_type: str = '',
        entity_id: str = '',
        metadata: dict = None,
    ) -> None:
        """Route notification to channels based on user preferences."""
        try:
            pref = NotificationPreference.objects_unscoped.get(
                tenant=tenant, user=user, event_type=event_type
            )
            in_app_enabled = pref.in_app_enabled
            email_enabled = pref.email_enabled
        except NotificationPreference.DoesNotExist:
            in_app_enabled = True
            email_enabled = True

        kwargs = dict(
            user=user,
            tenant=tenant,
            event_type=event_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else '',
            metadata=metadata or {},
        )

        if in_app_enabled:
            _CHANNELS[NotificationChannel.IN_APP].send(**kwargs)

        if email_enabled:
            _CHANNELS[NotificationChannel.EMAIL].send(**kwargs)

    @staticmethod
    def mark_read(notification: Notification) -> Notification:
        if notification.status != NotificationStatus.READ:
            notification.status = NotificationStatus.READ
            notification.read_at = timezone.now()
            notification.save(update_fields=['status', 'read_at', 'updated_at'])
        return notification

    @staticmethod
    def mark_all_read(user, tenant) -> int:
        now = timezone.now()
        updated = Notification.objects_unscoped.filter(
            tenant=tenant,
            recipient=user,
        ).exclude(status=NotificationStatus.READ).update(
            status=NotificationStatus.READ,
            read_at=now,
            updated_at=now,
        )
        return updated
