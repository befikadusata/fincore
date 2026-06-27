import hashlib
import hmac
import json
import pytest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing.constants import (
    BillingCycle, GatewayProvider, InvoiceStatus, PaymentStatus, SubscriptionStatus,
)
from apps.billing.middleware import FeatureGatingMiddleware
from apps.billing.models import Invoice, PaymentRecord, Subscription
from apps.billing.services.billing_service import BillingService
from apps.billing.services.gateways.chapa import ChapaGateway
from apps.saas.models import Membership, Plan, PlanFeature, Tenant, User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Billing Bank', slug='billing-bank')


@pytest.fixture
def user(db):
    return User.objects.create_user(email='admin@billing.com', password='pw')


@pytest.fixture
def plan(tenant):
    return Plan.objects_unscoped.create(
        tenant=tenant,
        name='Pro',
        slug='pro',
        monthly_price=5000,
        annual_price=50000,
        currency='ETB',
    )


@pytest.fixture
def plan_with_feature(plan):
    PlanFeature.objects.create(plan=plan, name='API Access', codename='api_access')
    return plan


@pytest.fixture
def subscription(tenant, plan):
    return Subscription.objects_unscoped.create(
        tenant=tenant,
        plan=plan,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )


def _make_signed_payload(data: dict, secret: str) -> tuple[bytes, str]:
    payload = json.dumps(data).encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return payload, sig


# ---------------------------------------------------------------------------
# Subscription Lifecycle
# ---------------------------------------------------------------------------

class TestSubscriptionLifecycle:
    def test_subscribe_creates_active_subscription(self, db, tenant, plan):
        sub = BillingService.subscribe(tenant, plan)
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.tenant == tenant
        assert sub.plan == plan
        assert sub.current_period_start is not None
        assert sub.current_period_end is not None

    def test_subscribe_with_trial_creates_trialing(self, db, tenant, plan):
        sub = BillingService.subscribe(tenant, plan, trial_days=14)
        assert sub.status == SubscriptionStatus.TRIALING
        assert sub.trial_end is not None

    def test_subscribe_without_trial_generates_invoice(self, db, tenant, plan):
        sub = BillingService.subscribe(tenant, plan)
        assert Invoice.objects_unscoped.filter(subscription=sub).count() == 1

    def test_subscribe_with_trial_skips_invoice(self, db, tenant, plan):
        sub = BillingService.subscribe(tenant, plan, trial_days=14)
        assert Invoice.objects_unscoped.filter(subscription=sub).count() == 0

    def test_subscribe_quarterly_sets_correct_period(self, db, tenant, plan):
        sub = BillingService.subscribe(tenant, plan, billing_cycle=BillingCycle.QUARTERLY)
        delta = sub.current_period_end - sub.current_period_start
        assert delta.days >= 89  # ~3 months

    def test_change_plan_updates_plan(self, db, tenant, plan, subscription):
        new_plan = Plan.objects_unscoped.create(
            tenant=tenant, name='Enterprise', slug='enterprise',
            monthly_price=10000, annual_price=100000, currency='ETB',
        )
        updated = BillingService.change_plan(subscription, new_plan)
        assert updated.plan == new_plan
        updated.refresh_from_db()
        assert updated.plan == new_plan

    def test_cancel_subscription(self, db, subscription):
        cancelled = BillingService.cancel_subscription(subscription)
        assert cancelled.status == SubscriptionStatus.CANCELLED
        assert cancelled.cancelled_at is not None
        cancelled.refresh_from_db()
        assert cancelled.status == SubscriptionStatus.CANCELLED

    def test_generate_invoice_monthly_uses_monthly_price(self, db, subscription, plan):
        invoice = BillingService.generate_invoice(subscription)
        assert invoice.amount == Decimal(plan.monthly_price)
        assert invoice.currency == plan.currency
        assert invoice.status == InvoiceStatus.ISSUED

    def test_generate_invoice_number_format(self, db, subscription):
        invoice = BillingService.generate_invoice(subscription)
        assert invoice.invoice_number.startswith('INV-BILLING-BANK-')

    def test_generate_invoice_annual_uses_annual_price(self, db, subscription, plan):
        subscription.billing_cycle = BillingCycle.ANNUALLY
        subscription.save()
        invoice = BillingService.generate_invoice(subscription)
        assert invoice.amount == Decimal(plan.annual_price)

    def test_generate_invoice_due_date_matches_period_end(self, db, subscription):
        invoice = BillingService.generate_invoice(subscription)
        assert invoice.due_date == subscription.current_period_end.date()


# ---------------------------------------------------------------------------
# Subscription Status Check (Celery beat logic)
# ---------------------------------------------------------------------------

class TestSubscriptionStatusCheck:
    def test_marks_active_with_expired_period_as_past_due(self, db, tenant, plan):
        sub = Subscription.objects_unscoped.create(
            tenant=tenant, plan=plan,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_period_end=timezone.now() - timedelta(hours=1),
        )
        BillingService.check_subscription_status()
        sub.refresh_from_db()
        assert sub.status == SubscriptionStatus.PAST_DUE

    def test_marks_long_past_due_as_expired(self, db, tenant, plan):
        sub = Subscription.objects_unscoped.create(
            tenant=tenant, plan=plan,
            status=SubscriptionStatus.PAST_DUE,
            billing_cycle=BillingCycle.MONTHLY,
            current_period_end=timezone.now() - timedelta(days=10),
        )
        BillingService.check_subscription_status()
        sub.refresh_from_db()
        assert sub.status == SubscriptionStatus.EXPIRED

    def test_active_within_period_unchanged(self, db, tenant, plan):
        sub = Subscription.objects_unscoped.create(
            tenant=tenant, plan=plan,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_period_end=timezone.now() + timedelta(days=10),
        )
        BillingService.check_subscription_status()
        sub.refresh_from_db()
        assert sub.status == SubscriptionStatus.ACTIVE

    def test_returns_counts(self, db, tenant, plan):
        Subscription.objects_unscoped.create(
            tenant=tenant, plan=plan,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_period_end=timezone.now() - timedelta(hours=1),
        )
        result = BillingService.check_subscription_status()
        assert result['marked_past_due'] == 1
        assert 'marked_expired' in result


# ---------------------------------------------------------------------------
# ChapaGateway
# ---------------------------------------------------------------------------

class TestChapaGateway:
    def test_initialize_payment_success(self):
        gateway = ChapaGateway(secret_key='test-key', webhook_secret='secret')
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'status': 'success',
            'data': {'checkout_url': 'https://checkout.chapa.co/pay/abc'},
        }
        with patch('requests.post', return_value=mock_resp):
            result = gateway.initialize_payment(
                amount=Decimal('500.00'),
                currency='ETB',
                callback_url='https://app.example.com/callback',
                reference='INV-BANK-202606-0001',
                customer_email='user@example.com',
                customer_name='Abebe Bekele',
            )
        assert result.checkout_url == 'https://checkout.chapa.co/pay/abc'
        assert result.reference == 'INV-BANK-202606-0001'

    def test_initialize_payment_api_error_raises(self):
        gateway = ChapaGateway(secret_key='test-key', webhook_secret='secret')
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'status': 'error', 'message': 'Bad request'}
        with patch('requests.post', return_value=mock_resp):
            with pytest.raises(ValueError, match='Chapa initialization failed'):
                gateway.initialize_payment(
                    amount=Decimal('500.00'),
                    currency='ETB',
                    callback_url='https://example.com/cb',
                    reference='REF-001',
                    customer_email='u@example.com',
                )

    def test_verify_payment_success(self):
        gateway = ChapaGateway(secret_key='test-key', webhook_secret='secret')
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'status': 'success',
            'data': {'status': 'success', 'amount': '500.00', 'currency': 'ETB'},
        }
        with patch('requests.get', return_value=mock_resp):
            result = gateway.verify_payment('REF-001')
        assert result.status == 'success'
        assert result.amount == Decimal('500.00')
        assert result.currency == 'ETB'

    def test_verify_payment_api_failure_returns_failed(self):
        gateway = ChapaGateway(secret_key='test-key', webhook_secret='secret')
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'status': 'error', 'message': 'Not found'}
        with patch('requests.get', return_value=mock_resp):
            result = gateway.verify_payment('BAD-REF')
        assert result.status == 'failed'

    def test_validate_webhook_signature_valid(self):
        secret = 'webhook-secret'
        gateway = ChapaGateway(secret_key='test-key', webhook_secret=secret)
        payload = b'{"tx_ref":"REF-001","status":"success"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert gateway.validate_webhook_signature(payload, sig) is True

    def test_validate_webhook_signature_invalid(self):
        gateway = ChapaGateway(secret_key='test-key', webhook_secret='real-secret')
        payload = b'{"tx_ref":"REF-001"}'
        assert gateway.validate_webhook_signature(payload, 'bad-signature') is False

    def test_validate_webhook_no_secret_returns_false(self):
        gateway = ChapaGateway(secret_key='test-key', webhook_secret='')
        assert gateway.validate_webhook_signature(b'data', 'any-sig') is False

    def test_initialize_passes_correct_fields(self):
        gateway = ChapaGateway(secret_key='sk-test', webhook_secret='ws')
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'status': 'success',
            'data': {'checkout_url': 'https://checkout.chapa.co/x'},
        }
        with patch('requests.post', return_value=mock_resp) as mock_post:
            gateway.initialize_payment(
                amount=Decimal('1000'),
                currency='ETB',
                callback_url='https://cb.example.com/',
                reference='TX-001',
                customer_email='test@example.com',
                customer_name='Liya Hailu',
            )
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs['json']
        assert body['first_name'] == 'Liya'
        assert body['last_name'] == 'Hailu'
        assert body['tx_ref'] == 'TX-001'
        assert call_kwargs.kwargs['headers']['Authorization'] == 'Bearer sk-test'


# ---------------------------------------------------------------------------
# Webhook Processing
# ---------------------------------------------------------------------------

class TestWebhookProcessing:
    def _create_invoice_and_record(self, subscription, invoice_number):
        invoice = Invoice.objects_unscoped.create(
            tenant=subscription.tenant,
            subscription=subscription,
            invoice_number=invoice_number,
            status=InvoiceStatus.ISSUED,
            amount=Decimal('5000'),
            currency='ETB',
            due_date=timezone.now().date(),
        )
        record = PaymentRecord.objects_unscoped.create(
            tenant=subscription.tenant,
            invoice=invoice,
            status=PaymentStatus.PENDING,
            amount=Decimal('5000'),
            currency='ETB',
            gateway_reference=invoice_number,
            gateway_provider=GatewayProvider.CHAPA,
        )
        return invoice, record

    def test_successful_payment_marks_invoice_paid(self, db, subscription):
        secret = 'test-webhook-secret'
        invoice, _ = self._create_invoice_and_record(subscription, 'INV-BB-202606-0001')
        payload, sig = _make_signed_payload(
            {'tx_ref': 'INV-BB-202606-0001', 'status': 'success'}, secret
        )
        gateway = ChapaGateway(secret_key='key', webhook_secret=secret)

        record = BillingService.process_webhook(payload, sig, gateway)

        assert record.status == PaymentStatus.COMPLETED
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.paid_at is not None

    def test_successful_payment_activates_past_due_subscription(self, db, subscription):
        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.save()
        secret = 'secret'
        invoice, _ = self._create_invoice_and_record(subscription, 'INV-BB-202606-0002')
        payload, sig = _make_signed_payload(
            {'tx_ref': 'INV-BB-202606-0002', 'status': 'success'}, secret
        )
        gateway = ChapaGateway(secret_key='k', webhook_secret=secret)
        BillingService.process_webhook(payload, sig, gateway)
        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.ACTIVE

    def test_failed_payment_leaves_invoice_unpaid(self, db, subscription):
        secret = 'test-secret'
        invoice, _ = self._create_invoice_and_record(subscription, 'INV-BB-202606-0003')
        payload, sig = _make_signed_payload(
            {'tx_ref': 'INV-BB-202606-0003', 'status': 'failed'}, secret
        )
        gateway = ChapaGateway(secret_key='k', webhook_secret=secret)
        with patch('apps.events.services.event_bus.EventBus.emit'):
            record = BillingService.process_webhook(payload, sig, gateway)
        assert record.status == PaymentStatus.FAILED
        invoice.refresh_from_db()
        assert invoice.status == InvoiceStatus.ISSUED

    def test_invalid_signature_raises_value_error(self, db, subscription):
        gateway = ChapaGateway(secret_key='key', webhook_secret='real-secret')
        payload = b'{"tx_ref":"REF","status":"success"}'
        with pytest.raises(ValueError, match='Invalid webhook signature'):
            BillingService.process_webhook(payload, 'bad-sig', gateway)

    def test_unknown_reference_raises_value_error(self, db, subscription):
        secret = 'secret'
        payload, sig = _make_signed_payload({'tx_ref': 'NONEXISTENT', 'status': 'success'}, secret)
        gateway = ChapaGateway(secret_key='k', webhook_secret=secret)
        with pytest.raises(ValueError, match='No invoice or payment record found'):
            BillingService.process_webhook(payload, sig, gateway)

    def test_webhook_creates_record_if_missing(self, db, subscription):
        secret = 'secret'
        Invoice.objects_unscoped.create(
            tenant=subscription.tenant,
            subscription=subscription,
            invoice_number='INV-BB-202606-0004',
            status=InvoiceStatus.ISSUED,
            amount=Decimal('5000'),
            currency='ETB',
            due_date=timezone.now().date(),
        )
        payload, sig = _make_signed_payload(
            {'tx_ref': 'INV-BB-202606-0004', 'status': 'success'}, secret
        )
        gateway = ChapaGateway(secret_key='k', webhook_secret=secret)
        record = BillingService.process_webhook(payload, sig, gateway)
        assert record.gateway_reference == 'INV-BB-202606-0004'
        assert record.status == PaymentStatus.COMPLETED


# ---------------------------------------------------------------------------
# Feature Gating Middleware
# ---------------------------------------------------------------------------

class TestFeatureGatingMiddleware:
    def _get_request(self):
        from django.test import RequestFactory
        return RequestFactory().get('/')

    def _view_func(self, required_feature=None):
        class ViewClass:
            pass
        if required_feature:
            ViewClass.required_plan_feature = required_feature
        return type('V', (), {'cls': ViewClass})()

    def test_no_required_feature_passes_through(self, db):
        middleware = FeatureGatingMiddleware(lambda req: None)
        result = middleware.process_view(self._get_request(), self._view_func(), [], {})
        assert result is None

    def test_no_tenant_context_passes_through(self, db):
        middleware = FeatureGatingMiddleware(lambda req: None)
        with patch('apps.billing.middleware.get_current_tenant', return_value=None):
            result = middleware.process_view(
                self._get_request(), self._view_func('api_access'), [], {}
            )
        assert result is None

    def test_no_subscription_returns_402(self, db, tenant):
        middleware = FeatureGatingMiddleware(lambda req: None)
        with patch('apps.billing.middleware.get_current_tenant', return_value=tenant):
            result = middleware.process_view(
                self._get_request(), self._view_func('api_access'), [], {}
            )
        assert result is not None
        assert result.status_code == 402

    def test_plan_without_feature_returns_403(self, db, tenant, subscription):
        middleware = FeatureGatingMiddleware(lambda req: None)
        with patch('apps.billing.middleware.get_current_tenant', return_value=tenant):
            result = middleware.process_view(
                self._get_request(), self._view_func('api_access'), [], {}
            )
        assert result is not None
        assert result.status_code == 403

    def test_plan_with_feature_passes(self, db, tenant, subscription, plan_with_feature):
        subscription.plan = plan_with_feature
        subscription.save()
        middleware = FeatureGatingMiddleware(lambda req: None)
        with patch('apps.billing.middleware.get_current_tenant', return_value=tenant):
            result = middleware.process_view(
                self._get_request(), self._view_func('api_access'), [], {}
            )
        assert result is None

    def test_trialing_subscription_also_passes(self, db, tenant, plan_with_feature):
        Subscription.objects_unscoped.create(
            tenant=tenant,
            plan=plan_with_feature,
            status=SubscriptionStatus.TRIALING,
            billing_cycle=BillingCycle.MONTHLY,
            current_period_end=timezone.now() + timedelta(days=14),
        )
        middleware = FeatureGatingMiddleware(lambda req: None)
        with patch('apps.billing.middleware.get_current_tenant', return_value=tenant):
            result = middleware.process_view(
                self._get_request(), self._view_func('api_access'), [], {}
            )
        assert result is None


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

class TestSubscriptionAPI:
    def _authed_client(self, user, tenant):
        from rest_framework_simplejwt.tokens import RefreshToken
        Membership.objects.create(user=user, tenant=tenant, status='active')
        client = APIClient()
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_X_TENANT_ID=str(tenant.id),
        )
        return client

    def test_list_subscriptions(self, db, tenant, user, subscription):
        client = self._authed_client(user, tenant)
        response = client.get('/api/v1/billing/subscriptions/')
        assert response.status_code == 200

    def test_create_subscription(self, db, tenant, user, plan):
        client = self._authed_client(user, tenant)
        response = client.post('/api/v1/billing/subscriptions/', {
            'plan': str(plan.id),
            'billing_cycle': 'monthly',
            'trial_days': 0,
        })
        assert response.status_code == 201
        assert response.data['status'] == SubscriptionStatus.ACTIVE

    def test_create_subscription_with_trial(self, db, tenant, user, plan):
        client = self._authed_client(user, tenant)
        response = client.post('/api/v1/billing/subscriptions/', {
            'plan': str(plan.id),
            'billing_cycle': 'monthly',
            'trial_days': 14,
        })
        assert response.status_code == 201
        assert response.data['status'] == SubscriptionStatus.TRIALING

    def test_cancel_subscription_action(self, db, tenant, user, subscription):
        client = self._authed_client(user, tenant)
        response = client.post(f'/api/v1/billing/subscriptions/{subscription.id}/cancel/')
        assert response.status_code == 200
        assert response.data['status'] == SubscriptionStatus.CANCELLED

    def test_change_plan_action(self, db, tenant, user, subscription):
        new_plan = Plan.objects_unscoped.create(
            tenant=tenant, name='Enterprise', slug='enterprise',
            monthly_price=10000, annual_price=100000, currency='ETB',
        )
        client = self._authed_client(user, tenant)
        response = client.post(
            f'/api/v1/billing/subscriptions/{subscription.id}/change-plan/',
            {'plan': str(new_plan.id)},
        )
        assert response.status_code == 200
        assert str(response.data['plan']) == str(new_plan.id)

    def test_generate_invoice_action(self, db, tenant, user, subscription):
        client = self._authed_client(user, tenant)
        response = client.post(
            f'/api/v1/billing/subscriptions/{subscription.id}/generate-invoice/'
        )
        assert response.status_code == 201
        assert response.data['status'] == InvoiceStatus.ISSUED

    def test_list_invoices(self, db, tenant, user, subscription):
        Invoice.objects_unscoped.create(
            tenant=tenant, subscription=subscription,
            invoice_number='INV-LISTING-001',
            status=InvoiceStatus.ISSUED,
            amount=Decimal('5000'), currency='ETB',
            due_date=timezone.now().date(),
        )
        client = self._authed_client(user, tenant)
        response = client.get('/api/v1/billing/invoices/')
        assert response.status_code == 200

    def test_unauthenticated_request_rejected(self, db, tenant, plan):
        client = APIClient()
        response = client.get('/api/v1/billing/subscriptions/')
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Chapa Webhook Endpoint
# ---------------------------------------------------------------------------

class TestChapaWebhookEndpoint:
    def _setup_payable_invoice(self, subscription, ref):
        invoice = Invoice.objects_unscoped.create(
            tenant=subscription.tenant, subscription=subscription,
            invoice_number=ref, status=InvoiceStatus.ISSUED,
            amount=Decimal('5000'), currency='ETB',
            due_date=timezone.now().date(),
        )
        PaymentRecord.objects_unscoped.create(
            tenant=subscription.tenant, invoice=invoice,
            status=PaymentStatus.PENDING, amount=Decimal('5000'),
            currency='ETB', gateway_reference=ref,
            gateway_provider=GatewayProvider.CHAPA,
        )
        return invoice

    def test_valid_webhook_returns_200(self, db, subscription):
        secret = 'test-webhook-secret'
        ref = 'INV-ENDPOINT-001'
        self._setup_payable_invoice(subscription, ref)
        payload, sig = _make_signed_payload({'tx_ref': ref, 'status': 'success'}, secret)

        client = APIClient()
        with patch(
            'apps.billing.api.webhooks.chapa.ChapaGateway',
            return_value=MagicMock(
                validate_webhook_signature=lambda p, s: True,
            ),
        ):
            response = client.post(
                '/api/v1/webhooks/chapa/',
                data=payload,
                content_type='application/json',
                HTTP_CHAPA_SIGNATURE=sig,
            )
        assert response.status_code == 200

    def test_invalid_signature_returns_400(self, db, subscription):
        client = APIClient()
        with patch(
            'apps.billing.api.webhooks.chapa.ChapaGateway',
            return_value=MagicMock(
                validate_webhook_signature=lambda p, s: False,
            ),
        ):
            response = client.post(
                '/api/v1/webhooks/chapa/',
                data=b'{"tx_ref":"BAD","status":"success"}',
                content_type='application/json',
                HTTP_CHAPA_SIGNATURE='bad-sig',
            )
        assert response.status_code == 400
