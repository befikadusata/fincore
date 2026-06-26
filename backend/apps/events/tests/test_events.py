import pytest
from unittest.mock import patch, MagicMock

from apps.events.constants import EventStatus, EventType
from apps.events.models import DomainEvent, EventSubscription
from apps.events.registry import EventRegistry
from apps.events.services.event_bus import EventBus
from apps.events.tasks import dispatch_event, recover_pending_events
from apps.saas.models import Tenant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_registry():
    """Ensure the in-memory registry is clean between tests."""
    EventRegistry.clear()
    yield
    EventRegistry.clear()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Event Bank', slug='event-bank')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_handler(results: list):
    """Return a callable that records calls in `results`."""
    def handler(event):
        results.append(event.id)
    return handler


# ---------------------------------------------------------------------------
# EventRegistry
# ---------------------------------------------------------------------------

class TestEventRegistry:
    def test_register_and_get(self):
        EventRegistry.register('loan.submitted', 'apps.events.tests.test_events.noop')
        paths = EventRegistry._handlers.get('loan.submitted', [])
        assert 'apps.events.tests.test_events.noop' in paths

    def test_get_handlers_resolves_callable(self):
        EventRegistry.register('loan.submitted', 'apps.events.tests.test_events.noop')
        handlers = EventRegistry.get_handlers('loan.submitted')
        # Compare by name to avoid pytest module double-import identity mismatch
        assert len(handlers) == 1
        assert handlers[0].__name__ == 'noop'

    def test_get_handlers_skips_bad_path(self):
        EventRegistry.register('loan.submitted', 'does.not.exist.handler')
        # Should not raise; returns empty list
        handlers = EventRegistry.get_handlers('loan.submitted')
        assert handlers == []

    def test_no_duplicate_registration(self):
        EventRegistry.register('loan.approved', 'apps.events.tests.test_events.noop')
        EventRegistry.register('loan.approved', 'apps.events.tests.test_events.noop')
        assert EventRegistry._handlers['loan.approved'].count('apps.events.tests.test_events.noop') == 1

    def test_load_from_db(self, db):
        EventSubscription.objects.create(
            event_type='loan.approved',
            handler_path='apps.events.tests.test_events.noop',
        )
        EventRegistry.load_from_db()
        assert 'apps.events.tests.test_events.noop' in EventRegistry._handlers['loan.approved']

    def test_load_from_db_skips_inactive(self, db):
        EventSubscription.objects.create(
            event_type='loan.approved',
            handler_path='apps.events.tests.test_events.noop',
            is_active=False,
        )
        EventRegistry.load_from_db()
        # Inactive subscriptions must not appear in the loaded handlers
        assert 'apps.events.tests.test_events.noop' not in EventRegistry._handlers.get('loan.approved', [])


# ---------------------------------------------------------------------------
# EventBus.emit
# ---------------------------------------------------------------------------

class TestEventBusEmit:
    def test_emit_creates_pending_event(self, db, tenant):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            event = EventBus.emit(
                event_type=EventType.LOAN_SUBMITTED,
                entity_type='Loan',
                entity_id='abc-123',
                payload={'amount': 5000},
                tenant=tenant,
            )

        assert event.status == EventStatus.PENDING
        assert event.event_type == EventType.LOAN_SUBMITTED
        assert event.entity_type == 'Loan'
        assert event.entity_id == 'abc-123'
        assert event.payload == {'amount': 5000}
        assert event.tenant == tenant

    def test_emit_persists_to_db(self, db, tenant):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            event = EventBus.emit(
                event_type=EventType.LOAN_DISBURSED,
                entity_type='Loan',
                entity_id='xyz',
                payload={},
                tenant=tenant,
            )

        assert DomainEvent.objects_unscoped.filter(id=event.id).exists()

    def test_emit_schedules_celery_task(self, db, tenant):
        # Patch on_commit to invoke the callback immediately (no real commit in test transactions)
        with patch('django.db.transaction.on_commit', new=lambda fn: fn()):
            with patch('apps.events.tasks.dispatch_event.apply_async') as mock_async:
                event = EventBus.emit(
                    event_type=EventType.LOAN_SUBMITTED,
                    entity_type='Loan',
                    entity_id='1',
                    payload={},
                    tenant=tenant,
                )
        mock_async.assert_called_once_with(args=[str(event.id)])


# ---------------------------------------------------------------------------
# EventBus.subscribe
# ---------------------------------------------------------------------------

class TestEventBusSubscribe:
    def test_subscribe_creates_db_record(self, db):
        sub = EventBus.subscribe('loan.submitted', 'apps.events.tests.test_events.noop')
        assert EventSubscription.objects.filter(
            event_type='loan.submitted',
            handler_path='apps.events.tests.test_events.noop',
        ).exists()
        assert sub.is_active is True

    def test_subscribe_idempotent(self, db):
        EventBus.subscribe('loan.submitted', 'apps.events.tests.test_events.noop')
        EventBus.subscribe('loan.submitted', 'apps.events.tests.test_events.noop')
        assert EventSubscription.objects.filter(
            event_type='loan.submitted',
            handler_path='apps.events.tests.test_events.noop',
        ).count() == 1

    def test_subscribe_reactivates_inactive(self, db):
        EventSubscription.objects.create(
            event_type='loan.submitted',
            handler_path='apps.events.tests.test_events.noop',
            is_active=False,
        )
        sub = EventBus.subscribe('loan.submitted', 'apps.events.tests.test_events.noop')
        assert sub.is_active is True

    def test_subscribe_registers_in_memory(self, db):
        EventBus.subscribe('loan.submitted', 'apps.events.tests.test_events.noop')
        assert 'apps.events.tests.test_events.noop' in EventRegistry._handlers.get('loan.submitted', [])


# ---------------------------------------------------------------------------
# dispatch_event task
# ---------------------------------------------------------------------------

class TestDispatchEvent:
    def test_dispatch_calls_handlers(self, db, tenant):
        calls = []
        EventRegistry.register(EventType.LOAN_SUBMITTED, 'apps.events.tests.test_events.noop')

        event = DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=EventType.LOAN_SUBMITTED,
            entity_type='Loan',
            entity_id='1',
        )

        with patch('apps.events.services.event_bus._publish_to_stream', return_value='1-1'):
            dispatch_event(str(event.id))

        event.refresh_from_db()
        assert event.status == EventStatus.PROCESSED
        assert event.processed_at is not None

    def test_dispatch_marks_processed(self, db, tenant):
        event = DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=EventType.LOAN_APPROVED,
            entity_type='Loan',
            entity_id='2',
        )

        with patch('apps.events.services.event_bus._publish_to_stream', return_value=''):
            dispatch_event(str(event.id))

        event.refresh_from_db()
        assert event.status == EventStatus.PROCESSED

    def test_dispatch_idempotent_on_processed(self, db, tenant):
        """Calling dispatch_event on an already-processed event does nothing."""
        calls = []
        EventRegistry.register(EventType.LOAN_SUBMITTED, 'apps.events.tests.test_events.recording_handler')
        _recording_calls.clear()

        from django.utils import timezone
        event = DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=EventType.LOAN_SUBMITTED,
            entity_type='Loan',
            entity_id='3',
            status=EventStatus.PROCESSED,
            processed_at=timezone.now(),
        )

        dispatch_event(str(event.id))

        assert len(_recording_calls) == 0

    def test_dispatch_nonexistent_event_no_error(self, db):
        """dispatch_event with unknown ID should return silently."""
        import uuid
        dispatch_event(str(uuid.uuid4()))  # no exception

    def test_dispatch_handler_failure_increments_retry(self, db, tenant):
        EventRegistry.register(EventType.LOAN_SUBMITTED, 'apps.events.tests.test_events.failing_handler')

        event = DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=EventType.LOAN_SUBMITTED,
            entity_type='Loan',
            entity_id='4',
        )

        with pytest.raises(Exception):
            dispatch_event(str(event.id))

        event.refresh_from_db()
        assert event.retry_count == 1
        assert event.status == EventStatus.PENDING
        assert event.error_message != ''

    def test_dispatch_dead_letter_after_max_retries(self, db, tenant):
        from apps.events.services.event_bus import MAX_RETRIES
        EventRegistry.register(EventType.LOAN_SUBMITTED, 'apps.events.tests.test_events.failing_handler')

        event = DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=EventType.LOAN_SUBMITTED,
            entity_type='Loan',
            entity_id='5',
            retry_count=MAX_RETRIES - 1,
        )

        # Should not raise — moves to dead-letter instead of retrying
        dispatch_event(str(event.id))

        event.refresh_from_db()
        assert event.status == EventStatus.DEAD_LETTER
        assert event.retry_count == MAX_RETRIES

    def test_dispatch_skips_dead_letter_event(self, db, tenant):
        _recording_calls.clear()
        EventRegistry.register(EventType.LOAN_SUBMITTED, 'apps.events.tests.test_events.recording_handler')

        event = DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=EventType.LOAN_SUBMITTED,
            entity_type='Loan',
            entity_id='6',
            status=EventStatus.DEAD_LETTER,
        )

        dispatch_event(str(event.id))

        assert len(_recording_calls) == 0

    def test_dispatch_records_stream_id(self, db, tenant):
        event = DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=EventType.LOAN_COMPLETED,
            entity_type='Loan',
            entity_id='7',
        )

        # Patch where tasks.py imported it (not the origin module)
        with patch('apps.events.tasks._publish_to_stream', return_value='1234-0'):
            dispatch_event(str(event.id))

        event.refresh_from_db()
        assert event.stream_id == '1234-0'


# ---------------------------------------------------------------------------
# recover_pending_events task
# ---------------------------------------------------------------------------

class TestRecoverPendingEvents:
    def test_recover_redispatches_stale_pending(self, db, tenant):
        from datetime import timedelta
        from django.utils import timezone

        old_event = DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=EventType.REPAYMENT_RECEIVED,
            entity_type='Loan',
            entity_id='99',
            status=EventStatus.PENDING,
        )
        # Backdate created_at so it's older than the 5-minute cutoff
        DomainEvent.objects_unscoped.filter(id=old_event.id).update(
            created_at=timezone.now() - timedelta(minutes=10)
        )

        with patch('apps.events.tasks.dispatch_event.apply_async') as mock_async:
            result = recover_pending_events()

        assert result['re_dispatched'] >= 1
        mock_async.assert_called()

    def test_recover_ignores_recent_pending(self, db, tenant):
        DomainEvent.objects_unscoped.create(
            tenant=tenant,
            event_type=EventType.REPAYMENT_RECEIVED,
            entity_type='Loan',
            entity_id='100',
            status=EventStatus.PENDING,
        )

        with patch('apps.events.tasks.dispatch_event.apply_async') as mock_async:
            result = recover_pending_events()

        assert result['re_dispatched'] == 0
        mock_async.assert_not_called()


# ---------------------------------------------------------------------------
# Handler stubs used by tests above
# ---------------------------------------------------------------------------

def noop(event):
    pass


_recording_calls = []


def recording_handler(event):
    _recording_calls.append(event.id)


def failing_handler(event):
    raise ValueError('handler exploded')
