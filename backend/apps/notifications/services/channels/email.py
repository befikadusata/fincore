import logging
from django.core.mail import send_mail
from django.conf import settings
from apps.notifications.services.channels.base import BaseChannel

logger = logging.getLogger(__name__)


class EmailChannel(BaseChannel):
    def send(self, user, tenant, event_type: str, title: str, body: str, entity_type: str = '', entity_id: str = '', metadata: dict = None) -> bool:
        from apps.notifications.models import Notification
        from apps.notifications.constants import NotificationChannel, NotificationStatus

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fincore.io')
        success = False
        try:
            send_mail(
                subject=title,
                message=body,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
            notification_status = NotificationStatus.SENT
            success = True
        except Exception:
            logger.exception('EmailChannel failed for user %s event %s', user.id, event_type)
            notification_status = NotificationStatus.FAILED

        try:
            Notification.objects_unscoped.create(
                tenant=tenant,
                recipient=user,
                event_type=event_type,
                channel=NotificationChannel.EMAIL,
                title=title,
                body=body,
                entity_type=entity_type,
                entity_id=entity_id,
                status=notification_status,
                metadata=metadata or {},
            )
        except Exception:
            logger.exception('EmailChannel failed to record notification for user %s', user.id)

        return success
