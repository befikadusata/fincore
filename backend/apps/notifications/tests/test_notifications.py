import pytest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.constants import NotificationChannel, NotificationStatus
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services.channels.in_app import InAppChannel
from apps.notifications.services.channels.email import EmailChannel
from apps.notifications.services.notification_service import NotificationService
from apps.saas.models import Membership, Tenant, User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Notify Bank', slug='notify-bank')


@pytest.fixture
def user(db):
    return User.objects.create_user(email='borrower@bank.com', password='pw')


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(email='admin@bank.com', password='pw')


@pytest.fixture
def notification(db, tenant, user):
    return Notification.objects_unscoped.create(
        tenant=tenant,
        recipient=user,
        event_type='loan.approved',
        channel=NotificationChannel.IN_APP,
        title='Loan Approved',
        body='Your loan was approved.',
        status=NotificationStatus.SENT,
    )


def _authed_client(user, tenant):
    Membership.objects.get_or_create(user=user, tenant=tenant, defaults={'status': 'active'})
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {token}',
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    return client


# ---------------------------------------------------------------------------
# InAppChannel
# ---------------------------------------------------------------------------

class TestInAppChannel:
    def test_send_creates_notification(self, db, tenant, user):
        ch = InAppChannel()
        result = ch.send(
            user=user, tenant=tenant, event_type='loan.approved',
            title='Approved', body='Your loan is approved.',
        )
        assert result is True
        notif = Notification.objects_unscoped.get(recipient=user, tenant=tenant)
        assert notif.channel == NotificationChannel.IN_APP
        assert notif.status == NotificationStatus.SENT
        assert notif.title == 'Approved'

    def test_send_stores_entity_info(self, db, tenant, user):
        ch = InAppChannel()
        ch.send(
            user=user, tenant=tenant, event_type='loan.disbursed',
            title='Disbursed', body='Funds sent.',
            entity_type='Loan', entity_id='abc-123',
        )
        notif = Notification.objects_unscoped.get(recipient=user)
        assert notif.entity_type == 'Loan'
        assert notif.entity_id == 'abc-123'


# ---------------------------------------------------------------------------
# EmailChannel
# ---------------------------------------------------------------------------

class TestEmailChannel:
    def test_send_calls_django_send_mail_and_creates_notification(self, db, tenant, user):
        ch = EmailChannel()
        with patch('apps.notifications.services.channels.email.send_mail') as mock_mail:
            result = ch.send(
                user=user, tenant=tenant, event_type='loan.approved',
                title='Approved', body='Your loan was approved.',
            )
        assert result is True
        mock_mail.assert_called_once()
        _, kwargs = mock_mail.call_args
        assert user.email in mock_mail.call_args[1].get('recipient_list', mock_mail.call_args[0][3:])
        notif = Notification.objects_unscoped.get(recipient=user, channel=NotificationChannel.EMAIL)
        assert notif.status == NotificationStatus.SENT

    def test_failed_email_records_failed_status(self, db, tenant, user):
        ch = EmailChannel()
        with patch('apps.notifications.services.channels.email.send_mail', side_effect=Exception('SMTP error')):
            result = ch.send(
                user=user, tenant=tenant, event_type='loan.approved',
                title='Approved', body='msg',
            )
        assert result is False
        notif = Notification.objects_unscoped.get(recipient=user, channel=NotificationChannel.EMAIL)
        assert notif.status == NotificationStatus.FAILED


# ---------------------------------------------------------------------------
# NotificationService
# ---------------------------------------------------------------------------

class TestNotificationService:
    def test_notify_sends_both_channels_by_default(self, db, tenant, user):
        with patch('apps.notifications.services.channels.email.send_mail'):
            NotificationService.notify(
                user=user, tenant=tenant,
                event_type='loan.approved',
                title='Approved', body='msg',
            )
        assert Notification.objects_unscoped.filter(recipient=user, channel=NotificationChannel.IN_APP).exists()
        assert Notification.objects_unscoped.filter(recipient=user, channel=NotificationChannel.EMAIL).exists()

    def test_notify_respects_in_app_disabled_preference(self, db, tenant, user):
        NotificationPreference.objects_unscoped.create(
            tenant=tenant, user=user, event_type='loan.approved',
            in_app_enabled=False, email_enabled=True,
        )
        with patch('apps.notifications.services.channels.email.send_mail'):
            NotificationService.notify(
                user=user, tenant=tenant,
                event_type='loan.approved',
                title='Approved', body='msg',
            )
        assert not Notification.objects_unscoped.filter(recipient=user, channel=NotificationChannel.IN_APP).exists()
        assert Notification.objects_unscoped.filter(recipient=user, channel=NotificationChannel.EMAIL).exists()

    def test_notify_respects_email_disabled_preference(self, db, tenant, user):
        NotificationPreference.objects_unscoped.create(
            tenant=tenant, user=user, event_type='loan.approved',
            in_app_enabled=True, email_enabled=False,
        )
        with patch('apps.notifications.services.channels.email.send_mail'):
            NotificationService.notify(
                user=user, tenant=tenant,
                event_type='loan.approved',
                title='Approved', body='msg',
            )
        assert Notification.objects_unscoped.filter(recipient=user, channel=NotificationChannel.IN_APP).exists()
        assert not Notification.objects_unscoped.filter(recipient=user, channel=NotificationChannel.EMAIL).exists()

    def test_notify_all_channels_disabled(self, db, tenant, user):
        NotificationPreference.objects_unscoped.create(
            tenant=tenant, user=user, event_type='loan.approved',
            in_app_enabled=False, email_enabled=False,
        )
        NotificationService.notify(
            user=user, tenant=tenant,
            event_type='loan.approved',
            title='Approved', body='msg',
        )
        assert Notification.objects_unscoped.filter(recipient=user).count() == 0

    def test_mark_read_updates_status_and_read_at(self, db, notification):
        assert notification.status == NotificationStatus.SENT
        updated = NotificationService.mark_read(notification)
        assert updated.status == NotificationStatus.READ
        assert updated.read_at is not None

    def test_mark_read_is_idempotent(self, db, notification):
        first = NotificationService.mark_read(notification)
        first_read_at = first.read_at
        second = NotificationService.mark_read(first)
        assert second.read_at == first_read_at

    def test_mark_all_read_updates_all_unread(self, db, tenant, user):
        for i in range(3):
            Notification.objects_unscoped.create(
                tenant=tenant, recipient=user,
                event_type='loan.approved', channel=NotificationChannel.IN_APP,
                title=f'N{i}', body='msg', status=NotificationStatus.SENT,
            )
        count = NotificationService.mark_all_read(user, tenant)
        assert count == 3
        remaining_unread = Notification.objects_unscoped.filter(
            tenant=tenant, recipient=user
        ).exclude(status=NotificationStatus.READ).count()
        assert remaining_unread == 0

    def test_mark_all_read_skips_already_read(self, db, tenant, user):
        Notification.objects_unscoped.create(
            tenant=tenant, recipient=user,
            event_type='loan.approved', channel=NotificationChannel.IN_APP,
            title='Already Read', body='msg', status=NotificationStatus.READ,
            read_at=timezone.now(),
        )
        Notification.objects_unscoped.create(
            tenant=tenant, recipient=user,
            event_type='loan.approved', channel=NotificationChannel.IN_APP,
            title='Unread', body='msg', status=NotificationStatus.SENT,
        )
        count = NotificationService.mark_all_read(user, tenant)
        assert count == 1


# ---------------------------------------------------------------------------
# Event Handlers
# ---------------------------------------------------------------------------

@pytest.fixture
def loan_product(db, tenant):
    from apps.finance.models.loan_product import LoanProduct
    from apps.finance.constants import InterestType
    return LoanProduct.objects_unscoped.create(
        tenant=tenant, name='Basic',
        interest_type=InterestType.FLAT, interest_rate=Decimal('10.0'),
        min_amount=Decimal('1000'), max_amount=Decimal('100000'),
        min_term_months=1, max_term_months=12, currency='ETB',
    )


@pytest.fixture
def loan(db, tenant, user, loan_product):
    from apps.finance.models.loan import Loan
    from apps.finance.constants import LoanStatus
    return Loan.objects_unscoped.create(
        tenant=tenant,
        product=loan_product,
        borrower=user,
        principal_amount=Decimal('10000'),
        interest_amount=Decimal('1000'),
        total_amount=Decimal('11000'),
        outstanding_balance=Decimal('11000'),
        term_months=3,
        status=LoanStatus.APPROVED,
    )


class TestNotificationHandlers:
    def _make_event(self, tenant, event_type, entity_id, payload=None):
        evt = MagicMock()
        evt.tenant = tenant
        evt.tenant_id = tenant.id
        evt.event_type = event_type
        evt.entity_type = 'Loan'
        evt.entity_id = str(entity_id)
        evt.payload = payload or {}
        return evt

    def test_handle_loan_approved_notifies_borrower(self, db, tenant, user, loan):
        from apps.notifications.handlers import handle_loan_approved
        with patch('apps.notifications.services.channels.email.send_mail'):
            handle_loan_approved(self._make_event(tenant, 'loan.approved', loan.id))
        assert Notification.objects_unscoped.filter(
            recipient=user, event_type='loan.approved', entity_type='Loan'
        ).exists()

    def test_handle_loan_disbursed_notifies_borrower(self, db, tenant, user, loan):
        from apps.notifications.handlers import handle_loan_disbursed
        with patch('apps.notifications.services.channels.email.send_mail'):
            handle_loan_disbursed(self._make_event(tenant, 'loan.disbursed', loan.id))
        assert Notification.objects_unscoped.filter(
            recipient=user, event_type='loan.disbursed'
        ).exists()

    def test_handle_loan_approved_missing_loan_is_noop(self, db, tenant):
        from apps.notifications.handlers import handle_loan_approved
        import uuid
        handle_loan_approved(self._make_event(tenant, 'loan.approved', uuid.uuid4()))
        assert Notification.objects_unscoped.count() == 0

    def test_handle_repayment_due_soon_notifies_borrower(self, db, tenant, user, loan):
        from apps.notifications.handlers import handle_repayment_due_soon
        payload = {
            'loan_id': str(loan.id),
            'due_date': '2026-07-01',
            'amount': '3667.00',
        }
        evt = self._make_event(tenant, 'repayment.due_soon', loan.id, payload=payload)
        with patch('apps.notifications.services.channels.email.send_mail'):
            handle_repayment_due_soon(evt)
        assert Notification.objects_unscoped.filter(
            recipient=user, event_type='repayment.due_soon'
        ).exists()

    def test_handle_workflow_step_assigned_notifies_assignee(self, db, tenant, user):
        from apps.notifications.handlers import handle_workflow_step_assigned
        payload = {'assignee_id': str(user.id), 'step_name': 'Credit Review'}
        evt = MagicMock()
        evt.tenant = tenant
        evt.tenant_id = tenant.id
        evt.event_type = 'workflow.step_assigned'
        evt.entity_type = 'WorkflowInstance'
        evt.entity_id = 'inst-123'
        evt.payload = payload
        with patch('apps.notifications.services.channels.email.send_mail'):
            handle_workflow_step_assigned(evt)
        notif = Notification.objects_unscoped.filter(
            recipient=user, event_type='workflow.step_assigned'
        ).first()
        assert notif is not None
        assert 'Credit Review' in notif.body

    def test_handle_workflow_step_assigned_no_assignee_id_is_noop(self, db, tenant):
        from apps.notifications.handlers import handle_workflow_step_assigned
        evt = MagicMock()
        evt.tenant = tenant
        evt.payload = {}
        handle_workflow_step_assigned(evt)
        assert Notification.objects_unscoped.count() == 0

    def test_handle_subscription_payment_failed_notifies_admins(self, db, tenant, admin_user):
        from apps.notifications.handlers import handle_subscription_payment_failed
        from apps.saas.models import Role
        membership = Membership.objects.create(user=admin_user, tenant=tenant, status='active')
        role = Role.objects_unscoped.create(tenant=tenant, name='Admin', slug='admin')
        role.membership.add(membership)

        evt = MagicMock()
        evt.tenant = tenant
        evt.tenant_id = tenant.id
        evt.event_type = 'subscription.payment_failed'
        evt.payload = {}

        with patch('apps.notifications.services.channels.email.send_mail'):
            handle_subscription_payment_failed(evt)

        assert Notification.objects_unscoped.filter(
            recipient=admin_user, event_type='subscription.payment_failed'
        ).exists()

    def test_handle_subscription_payment_failed_no_admins_is_noop(self, db, tenant):
        from apps.notifications.handlers import handle_subscription_payment_failed
        evt = MagicMock()
        evt.tenant = tenant
        evt.tenant_id = tenant.id
        evt.event_type = 'subscription.payment_failed'
        evt.payload = {}
        handle_subscription_payment_failed(evt)
        assert Notification.objects_unscoped.count() == 0


# ---------------------------------------------------------------------------
# Due-Soon Reminder Task
# ---------------------------------------------------------------------------

class TestDueSoonReminderTask:
    def test_emits_event_for_installments_due_in_3_days(self, db, tenant, user, loan):
        from apps.finance.models.repayment_schedule import RepaymentSchedule
        from apps.finance.constants import RepaymentStatus
        from apps.notifications.tasks import send_repayment_due_reminders

        target = (timezone.now() + timedelta(days=3)).date()
        RepaymentSchedule.objects_unscoped.create(
            tenant=tenant, loan=loan, installment_number=1,
            due_date=target,
            principal_amount=Decimal('3333'), interest_amount=Decimal('334'),
            total_amount=Decimal('3667'), status=RepaymentStatus.PENDING,
        )

        with patch('apps.events.services.event_bus.EventBus.emit') as mock_emit:
            send_repayment_due_reminders()

        mock_emit.assert_called_once()
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs['event_type'] == 'repayment.due_soon'

    def test_skips_paid_installments(self, db, tenant, user, loan):
        from apps.finance.models.repayment_schedule import RepaymentSchedule
        from apps.finance.constants import RepaymentStatus
        from apps.notifications.tasks import send_repayment_due_reminders

        target = (timezone.now() + timedelta(days=3)).date()
        RepaymentSchedule.objects_unscoped.create(
            tenant=tenant, loan=loan, installment_number=1,
            due_date=target,
            principal_amount=Decimal('3333'), interest_amount=Decimal('334'),
            total_amount=Decimal('3667'), status=RepaymentStatus.PAID,
        )

        with patch('apps.events.services.event_bus.EventBus.emit') as mock_emit:
            send_repayment_due_reminders()

        mock_emit.assert_not_called()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

class TestNotificationAPI:
    def test_list_returns_only_own_notifications(self, db, tenant, user, notification):
        client = _authed_client(user, tenant)
        response = client.get('/api/v1/notifications/')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['title'] == 'Loan Approved'

    def test_list_excludes_other_user_notifications(self, db, tenant, user, admin_user, notification):
        other_client = _authed_client(admin_user, tenant)
        response = other_client.get('/api/v1/notifications/')
        assert response.status_code == 200
        assert len(response.data['results']) == 0

    def test_mark_read_action(self, db, tenant, user, notification):
        client = _authed_client(user, tenant)
        response = client.post(f'/api/v1/notifications/{notification.id}/mark-read/')
        assert response.status_code == 200
        assert response.data['status'] == NotificationStatus.READ

    def test_mark_all_read_action(self, db, tenant, user):
        for i in range(2):
            Notification.objects_unscoped.create(
                tenant=tenant, recipient=user,
                event_type='loan.approved', channel=NotificationChannel.IN_APP,
                title=f'N{i}', body='msg', status=NotificationStatus.SENT,
            )
        client = _authed_client(user, tenant)
        response = client.post('/api/v1/notifications/mark-all-read/')
        assert response.status_code == 200
        assert response.data['marked_read'] == 2

    def test_unauthenticated_returns_401(self, db):
        response = APIClient().get('/api/v1/notifications/')
        assert response.status_code == 401


class TestNotificationPreferenceAPI:
    def test_create_preference(self, db, tenant, user):
        client = _authed_client(user, tenant)
        response = client.post('/api/v1/notifications/preferences/', {
            'event_type': 'loan.approved',
            'in_app_enabled': True,
            'email_enabled': False,
        })
        assert response.status_code == 201
        pref = NotificationPreference.objects_unscoped.get(tenant=tenant, user=user)
        assert pref.email_enabled is False

    def test_list_preferences(self, db, tenant, user):
        NotificationPreference.objects_unscoped.create(
            tenant=tenant, user=user, event_type='loan.approved',
            in_app_enabled=True, email_enabled=True,
        )
        client = _authed_client(user, tenant)
        response = client.get('/api/v1/notifications/preferences/')
        assert response.status_code == 200
        assert len(response.data['results']) == 1

    def test_update_preference(self, db, tenant, user):
        pref = NotificationPreference.objects_unscoped.create(
            tenant=tenant, user=user, event_type='loan.approved',
            in_app_enabled=True, email_enabled=True,
        )
        client = _authed_client(user, tenant)
        response = client.patch(f'/api/v1/notifications/preferences/{pref.id}/', {
            'email_enabled': False,
        })
        assert response.status_code == 200
        pref.refresh_from_db()
        assert pref.email_enabled is False
