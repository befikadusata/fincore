import logging

from django.utils import timezone

from apps.events.constants import EventStatus
from apps.events.services.event_bus import MAX_RETRIES, _publish_to_stream
from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name='events.dispatch_event', max_retries=MAX_RETRIES)
def dispatch_event(self, event_id: str):
    """
    Load a DomainEvent by ID, call all registered handlers, and mark it PROCESSED.
    On failure: retry with exponential backoff up to MAX_RETRIES, then DEAD_LETTER.
    """
    from apps.events.models import DomainEvent
    from apps.events.registry import EventRegistry

    try:
        event = DomainEvent.objects_unscoped.get(id=event_id)
    except DomainEvent.DoesNotExist:
        return

    if event.status in (EventStatus.PROCESSED, EventStatus.DEAD_LETTER):
        return

    event.status = EventStatus.PROCESSING
    event.save(update_fields=['status', 'updated_at'])

    try:
        handlers = EventRegistry.get_handlers(event.event_type)
        for handler in handlers:
            handler(event)

        stream_id = _publish_to_stream(event)

        event.status = EventStatus.PROCESSED
        event.processed_at = timezone.now()
        event.stream_id = stream_id
        event.save(update_fields=['status', 'processed_at', 'stream_id', 'updated_at'])

    except Exception as exc:
        event.retry_count += 1
        event.error_message = str(exc)[:500]

        if event.retry_count >= MAX_RETRIES:
            event.status = EventStatus.DEAD_LETTER
            event.save(update_fields=['status', 'retry_count', 'error_message', 'updated_at'])
            logger.error('Event %s moved to dead-letter after %d retries', event_id, MAX_RETRIES)
            return

        event.status = EventStatus.PENDING
        event.save(update_fields=['status', 'retry_count', 'error_message', 'updated_at'])

        countdown = 2 ** event.retry_count
        raise self.retry(exc=exc, countdown=countdown)


@app.task(name='events.recover_pending_events')
def recover_pending_events():
    """
    Beat task: re-dispatch PENDING events older than 5 minutes that were
    never picked up (e.g. worker was down when on_commit fired).
    """
    from datetime import timedelta
    from apps.events.models import DomainEvent

    cutoff = timezone.now() - timedelta(minutes=5)
    stale = DomainEvent.objects_unscoped.filter(
        status=EventStatus.PENDING,
        created_at__lt=cutoff,
    ).values_list('id', flat=True)[:100]

    count = 0
    for event_id in stale:
        dispatch_event.apply_async(args=[str(event_id)])
        count += 1

    return {'re_dispatched': count}
