import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_repayment_due_reminders():
    """Emit repayment.due_soon events for installments due in exactly 3 days."""
    from apps.finance.models.repayment_schedule import RepaymentSchedule
    from apps.finance.constants import RepaymentStatus
    from apps.events.services.event_bus import EventBus
    from apps.events.constants import EventType

    target_date = (timezone.now() + timedelta(days=3)).date()

    installments = (
        RepaymentSchedule.objects_unscoped
        .filter(due_date=target_date, status__in=[RepaymentStatus.PENDING, RepaymentStatus.PARTIAL])
        .select_related('loan__tenant')
    )

    for installment in installments:
        loan = installment.loan
        try:
            EventBus.emit(
                event_type=EventType.REPAYMENT_DUE_SOON,
                entity_type='RepaymentSchedule',
                entity_id=str(installment.id),
                payload={
                    'loan_id': str(loan.id),
                    'installment_number': installment.installment_number,
                    'due_date': str(installment.due_date),
                    'amount': str(installment.total_amount - installment.amount_paid),
                },
                tenant=loan.tenant,
            )
        except Exception:
            logger.exception('Failed to emit due_soon event for installment %s', installment.id)
