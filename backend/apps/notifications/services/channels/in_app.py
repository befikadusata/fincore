import logging
from apps.notifications.services.channels.base import BaseChannel

logger = logging.getLogger(__name__)


class InAppChannel(BaseChannel):
    def send(self, user, tenant, event_type: str, title: str, body: str, entity_type: str = '', entity_id: str = '', metadata: dict = None) -> bool:
        from apps.notifications.models import Notification
        from apps.notifications.constants import NotificationChannel, NotificationStatus
        try:
            Notification.objects_unscoped.create(
                tenant=tenant,
                recipient=user,
                event_type=event_type,
                channel=NotificationChannel.IN_APP,
                title=title,
                body=body,
                entity_type=entity_type,
                entity_id=entity_id,
                status=NotificationStatus.SENT,
                metadata=metadata or {},
            )
            return True
        except Exception:
            logger.exception('InAppChannel failed for user %s event %s', user.id, event_type)
            return False
