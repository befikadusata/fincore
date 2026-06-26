import logging

from django.db import transaction
from django.utils import timezone

from apps.events.constants import EventStatus
from apps.events.models import DomainEvent, EventSubscription
from apps.events.registry import EventRegistry

logger = logging.getLogger(__name__)

STREAM_KEY_PREFIX = 'fincore:events'
MAX_RETRIES = 5


def _get_redis():
    try:
        import redis as redis_lib
        from django.conf import settings
        client = redis_lib.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def _publish_to_stream(event: DomainEvent) -> str:
    """Push event to Redis Stream; returns stream message ID or empty string."""
    r = _get_redis()
    if r is None:
        return ''
    try:
        stream_key = f'{STREAM_KEY_PREFIX}:{event.event_type}'
        return r.xadd(stream_key, {
            'event_id': str(event.id),
            'event_type': event.event_type,
            'entity_type': event.entity_type,
            'entity_id': str(event.entity_id),
            'tenant_id': str(event.tenant_id),
        }) or ''
    except Exception:
        logger.debug('Redis Stream publish failed for event %s', event.id)
        return ''


class EventBus:
    MAX_RETRIES = MAX_RETRIES

    @staticmethod
    def emit(event_type: str, entity_type: str, entity_id: str, payload: dict, tenant) -> DomainEvent:
        """
        Persist a DomainEvent and schedule async processing via Celery.
        The Celery task is dispatched inside on_commit so rolled-back transactions
        never produce orphaned events.
        """
        event = DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            payload=payload,
            status=EventStatus.PENDING,
        )

        event_id = str(event.id)

        def _dispatch():
            from apps.events.tasks import dispatch_event
            dispatch_event.apply_async(args=[event_id])

        transaction.on_commit(_dispatch)
        return event

    @staticmethod
    def subscribe(event_type: str, handler_path: str) -> EventSubscription:
        """Register a handler for an event type in DB and in-memory registry."""
        sub, _ = EventSubscription.objects.get_or_create(
            event_type=event_type,
            handler_path=handler_path,
            defaults={'is_active': True},
        )
        if not sub.is_active:
            sub.is_active = True
            sub.save(update_fields=['is_active', 'updated_at'])
        EventRegistry.register(event_type, handler_path)
        return sub
