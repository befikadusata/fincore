import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.billing.constants import (
    BillingCycle, GatewayProvider, InvoiceStatus, PaymentStatus, SubscriptionStatus,
)
from apps.billing.models import Invoice, PaymentRecord, Subscription

logger = logging.getLogger(__name__)

_BILLING_CYCLE_MONTHS = {
    BillingCycle.MONTHLY: 1,
    BillingCycle.QUARTERLY: 3,
    BillingCycle.ANNUALLY: 12,
}


def _generate_invoice_number(tenant) -> str:
    now = timezone.now()
    count = Invoice.objects_unscoped.filter(tenant=tenant).count() + 1
    return f'INV-{tenant.slug.upper()}-{now.strftime("%Y%m")}-{count:04d}'


class BillingService:
    @staticmethod
    @transaction.atomic
    def subscribe(
        tenant,
        plan,
        billing_cycle: str = BillingCycle.MONTHLY,
        gateway_provider: str = GatewayProvider.CHAPA,
        trial_days: int = 0,
    ) -> Subscription:
        now = timezone.now()
        trial_end = now + timedelta(days=trial_days) if trial_days else None
        months = _BILLING_CYCLE_MONTHS.get(billing_cycle, 1)
        period_end = now + timedelta(days=30 * months)
        status = SubscriptionStatus.TRIALING if trial_days else SubscriptionStatus.ACTIVE

        subscription = Subscription.objects_unscoped.create(
            tenant=tenant,
            plan=plan,
            status=status,
            billing_cycle=billing_cycle,
            gateway_provider=gateway_provider,
            current_period_start=now,
            current_period_end=period_end,
            trial_end=trial_end,
        )

        if not trial_days:
            BillingService.generate_invoice(subscription)

        return subscription

    @staticmethod
    @transaction.atomic
    def change_plan(subscription: Subscription, new_plan) -> Subscription:
        subscription.plan = new_plan
        subscription.save(update_fields=['plan', 'updated_at'])
        return subscription

    @staticmethod
    @transaction.atomic
    def cancel_subscription(subscription: Subscription) -> Subscription:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = timezone.now()
        subscription.save(update_fields=['status', 'cancelled_at', 'updated_at'])
        return subscription

    @staticmethod
    @transaction.atomic
    def generate_invoice(subscription: Subscription) -> Invoice:
        plan = subscription.plan
        if subscription.billing_cycle == BillingCycle.ANNUALLY:
            amount = Decimal(plan.annual_price)
        else:
            amount = Decimal(plan.monthly_price)

        due_date = (
            subscription.current_period_end.date()
            if subscription.current_period_end
            else (timezone.now() + timedelta(days=7)).date()
        )

        return Invoice.objects_unscoped.create(
            tenant=subscription.tenant,
            subscription=subscription,
            invoice_number=_generate_invoice_number(subscription.tenant),
            status=InvoiceStatus.ISSUED,
            amount=amount,
            currency=plan.currency,
            due_date=due_date,
        )

    @staticmethod
    @transaction.atomic
    def process_webhook(payload: bytes, signature: str, gateway) -> PaymentRecord:
        if not gateway.validate_webhook_signature(payload, signature):
            raise ValueError('Invalid webhook signature')

        import json
        data = json.loads(payload)
        tx_ref = data.get('tx_ref') or data.get('trx_ref') or data.get('reference', '')
        chapa_status = data.get('status', '')

        record = PaymentRecord.objects_unscoped.filter(gateway_reference=tx_ref).first()
        if not record:
            invoice = Invoice.objects_unscoped.filter(invoice_number=tx_ref).first()
            if not invoice:
                raise ValueError(f'No invoice or payment record found for reference: {tx_ref}')
            record = PaymentRecord.objects_unscoped.create(
                tenant=invoice.tenant,
                invoice=invoice,
                status=PaymentStatus.PENDING,
                amount=invoice.amount,
                currency=invoice.currency,
                gateway_reference=tx_ref,
                gateway_provider=GatewayProvider.CHAPA,
                metadata=data,
            )

        mapped_status = {
            'success': PaymentStatus.COMPLETED,
            'failed': PaymentStatus.FAILED,
        }.get(chapa_status.lower(), PaymentStatus.PENDING)

        record.status = mapped_status
        record.metadata = data
        record.save(update_fields=['status', 'metadata', 'updated_at'])

        if mapped_status == PaymentStatus.COMPLETED:
            invoice = record.invoice
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = timezone.now()
            invoice.save(update_fields=['status', 'paid_at', 'updated_at'])

            subscription = invoice.subscription
            if subscription.status in [SubscriptionStatus.PAST_DUE, SubscriptionStatus.TRIALING]:
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.save(update_fields=['status', 'updated_at'])

        elif mapped_status == PaymentStatus.FAILED:
            try:
                from apps.events.services.event_bus import EventBus
                EventBus.emit(
                    event_type='subscription.payment_failed',
                    entity_type='Invoice',
                    entity_id=str(record.invoice_id),
                    payload={'invoice_id': str(record.invoice_id), 'reference': tx_ref},
                    tenant=record.tenant,
                )
            except Exception:
                logger.debug('Failed to emit subscription.payment_failed for invoice %s', record.invoice_id)

        return record

    @staticmethod
    def check_subscription_status() -> dict:
        now = timezone.now()

        past_due_count = Subscription.objects_unscoped.filter(
            status=SubscriptionStatus.ACTIVE,
            current_period_end__lt=now,
        ).update(status=SubscriptionStatus.PAST_DUE, updated_at=now)

        grace_cutoff = now - timedelta(days=7)
        expired_count = Subscription.objects_unscoped.filter(
            status=SubscriptionStatus.PAST_DUE,
            current_period_end__lt=grace_cutoff,
        ).update(status=SubscriptionStatus.EXPIRED, updated_at=now)

        past_due_subs = list(
            Subscription.objects_unscoped.filter(
                status=SubscriptionStatus.PAST_DUE
            ).select_related('tenant')
        )

        for sub in past_due_subs:
            try:
                from apps.events.services.event_bus import EventBus
                EventBus.emit(
                    event_type='subscription.payment_failed',
                    entity_type='Subscription',
                    entity_id=str(sub.id),
                    payload={'subscription_id': str(sub.id), 'tenant_id': str(sub.tenant_id)},
                    tenant=sub.tenant,
                )
            except Exception:
                logger.debug('Failed to emit subscription.payment_failed for %s', sub.id)

        return {
            'marked_past_due': past_due_count,
            'marked_expired': expired_count,
            'payment_failed_notifications': len(past_due_subs),
        }
