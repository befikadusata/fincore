import calendar
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.finance.constants import (
    LoanStatus,
    RepaymentStatus,
    TransactionType,
    TransactionStatus,
)
from apps.finance.models.account import Account
from apps.finance.models.repayment_schedule import RepaymentSchedule
from apps.finance.models.wallet import Wallet
from apps.finance.services.ledger_service import LedgerService
from apps.finance.services.wallet_service import WalletService
from apps.finance.state_machines.loan_state_machine import loan_state_machine
from core.exceptions import InsufficientFundsError

logger = logging.getLogger(__name__)


def _add_months(dt, months):
    """Return a date that is `months` calendar months after `dt`."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


class RepaymentService:
    @staticmethod
    @transaction.atomic
    def generate_schedule(loan) -> list:
        from apps.finance.services.loan_service import LoanService

        # Idempotent: replace any existing schedule
        RepaymentSchedule.objects_unscoped.filter(loan=loan).delete()

        schedule_data = LoanService.compute_schedule(loan)

        ref_date = loan.disbursed_at.date() if loan.disbursed_at else timezone.now().date()

        rows = []
        for item in schedule_data['installments']:
            due_date = _add_months(ref_date, item['installment'])
            rows.append(RepaymentSchedule(
                tenant=loan.tenant,
                loan=loan,
                installment_number=item['installment'],
                due_date=due_date,
                principal_amount=Decimal(item['principal']),
                interest_amount=Decimal(item['interest']),
                total_amount=Decimal(item['payment']),
            ))

        return RepaymentSchedule.objects_unscoped.bulk_create(rows)

    @staticmethod
    @transaction.atomic
    def process_repayment(loan, amount: Decimal, idempotency_key: str = ''):
        from apps.finance.models.loan import Transaction

        if idempotency_key:
            existing = Transaction.objects_unscoped.filter(
                tenant=loan.tenant, idempotency_key=idempotency_key
            ).first()
            if existing:
                return existing

        if loan.status != LoanStatus.ACTIVE:
            raise ValueError(f"Cannot repay a {loan.status} loan")
        if amount <= Decimal('0'):
            raise ValueError("Repayment amount must be positive")

        # Allocate payment to installments oldest-first
        installments = list(
            RepaymentSchedule.objects_unscoped.filter(
                tenant=loan.tenant,
                loan=loan,
                status__in=[RepaymentStatus.PENDING, RepaymentStatus.PARTIAL, RepaymentStatus.OVERDUE],
            ).order_by('installment_number')
        )

        remaining = amount
        total_principal = Decimal('0')
        total_interest = Decimal('0')
        total_penalty = Decimal('0')

        for inst in installments:
            if remaining <= Decimal('0'):
                break

            outstanding = inst.total_amount + inst.penalty_amount - inst.amount_paid
            to_pay = min(remaining, outstanding)

            # Split to_pay: penalty first, then interest (pro-rata from inst.total_amount), then principal
            penalty_outstanding = inst.penalty_amount
            penalty_pay = min(to_pay, penalty_outstanding)
            after_penalty = to_pay - penalty_pay

            if inst.total_amount > Decimal('0'):
                interest_pay = (after_penalty * inst.interest_amount / inst.total_amount).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                principal_pay = after_penalty - interest_pay
            else:
                interest_pay = Decimal('0')
                principal_pay = after_penalty

            total_principal += principal_pay
            total_interest += interest_pay
            total_penalty += penalty_pay

            inst.amount_paid += to_pay
            remaining -= to_pay

            if inst.amount_paid >= inst.total_amount + inst.penalty_amount:
                inst.status = RepaymentStatus.PAID
                inst.paid_at = timezone.now()
            else:
                inst.status = RepaymentStatus.PARTIAL

            inst.save(update_fields=['amount_paid', 'status', 'paid_at', 'updated_at'])

        total_repaid = total_principal + total_interest + total_penalty
        if total_repaid <= Decimal('0'):
            raise ValueError("No outstanding installments to repay")

        reference = f'REPAY-{loan.pk}-{uuid.uuid4().hex[:8]}'

        loan_receivable = Account.objects_unscoped.get(tenant=loan.tenant, code='1100')

        # DR Borrower Wallet, CR Loan Receivable (full repaid amount)
        WalletService.debit(
            wallet=Wallet.objects_unscoped.get(tenant=loan.tenant, owner=loan.borrower),
            amount=total_repaid,
            reference=reference,
            destination_account=loan_receivable,
        )

        # DR Loan Receivable, CR Interest Revenue (interest portion)
        if total_interest > Decimal('0'):
            interest_revenue = Account.objects_unscoped.get(tenant=loan.tenant, code='4000')
            LedgerService.create_entry(
                debit_account=loan_receivable,
                credit_account=interest_revenue,
                amount=total_interest,
                reference=reference,
            )

        # DR Loan Receivable, CR Penalty Revenue (penalty portion)
        if total_penalty > Decimal('0'):
            penalty_revenue = Account.objects_unscoped.get(tenant=loan.tenant, code='4200')
            LedgerService.create_entry(
                debit_account=loan_receivable,
                credit_account=penalty_revenue,
                amount=total_penalty,
                reference=reference,
            )

        # Update loan outstanding balance
        loan.outstanding_balance = max(loan.outstanding_balance - total_repaid, Decimal('0'))

        still_outstanding = RepaymentSchedule.objects_unscoped.filter(
            loan=loan,
            status__in=[RepaymentStatus.PENDING, RepaymentStatus.PARTIAL, RepaymentStatus.OVERDUE],
        ).exists()

        if not still_outstanding or loan.outstanding_balance <= Decimal('0'):
            loan_state_machine.transition(loan, 'status', LoanStatus.COMPLETED)
            loan.completed_at = timezone.now()
            loan.save(update_fields=['outstanding_balance', 'completed_at', 'updated_at'])
        else:
            loan.save(update_fields=['outstanding_balance', 'updated_at'])

        txn = Transaction.objects_unscoped.create(
            tenant=loan.tenant,
            loan=loan,
            wallet=Wallet.objects_unscoped.get(tenant=loan.tenant, owner=loan.borrower),
            transaction_type=TransactionType.REPAYMENT,
            amount=total_repaid,
            status=TransactionStatus.COMPLETED,
            reference=reference,
            idempotency_key=idempotency_key,
        )

        _emit_repayment_events(loan, total_repaid, reference)
        return txn

    @staticmethod
    def check_overdue() -> int:
        today = timezone.now().date()
        base_qs = RepaymentSchedule.objects_unscoped.filter(
            status__in=[RepaymentStatus.PENDING, RepaymentStatus.PARTIAL],
            due_date__lt=today,
        )
        affected = list(base_qs.values('loan_id', 'tenant_id').distinct())
        count = base_qs.update(status=RepaymentStatus.OVERDUE)
        if affected:
            _emit_loan_overdue_events(affected)
        return count

    @staticmethod
    def apply_penalty(installment, penalty_amount: Decimal = None) -> RepaymentSchedule:
        if installment.status != RepaymentStatus.OVERDUE:
            raise ValueError("Can only apply penalty to overdue installments")

        if penalty_amount is None:
            penalty_rate = Decimal(
                str(installment.loan.product.fees_config.get('penalty_rate_pct', 1.0))
            )
            penalty_amount = (installment.total_amount * penalty_rate / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        installment.penalty_amount += penalty_amount
        installment.save(update_fields=['penalty_amount', 'updated_at'])
        return installment


def _emit_repayment_events(loan, amount: Decimal, reference: str) -> None:
    try:
        from apps.events.constants import EventType
        from apps.events.services.event_bus import EventBus
        EventBus.emit(
            event_type=EventType.REPAYMENT_RECEIVED,
            entity_type='Loan',
            entity_id=str(loan.pk),
            payload={
                'loan_id': str(loan.pk),
                'amount': str(amount),
                'reference': reference,
                'loan_status': loan.status,
            },
            tenant=loan.tenant,
        )
        if loan.status == LoanStatus.COMPLETED:
            EventBus.emit(
                event_type=EventType.LOAN_COMPLETED,
                entity_type='Loan',
                entity_id=str(loan.pk),
                payload={'loan_id': str(loan.pk)},
                tenant=loan.tenant,
            )
    except Exception:
        logger.debug('Failed to emit repayment events for loan %s', loan.pk)


def _emit_loan_overdue_events(affected: list) -> None:
    try:
        from apps.events.constants import EventType
        from apps.events.services.event_bus import EventBus
        from apps.saas.models import Tenant

        tenant_ids = {row['tenant_id'] for row in affected}
        tenant_map = {t.id: t for t in Tenant.objects.filter(id__in=tenant_ids)}

        for row in affected:
            tenant = tenant_map.get(row['tenant_id'])
            if not tenant:
                continue
            try:
                EventBus.emit(
                    event_type=EventType.LOAN_OVERDUE,
                    entity_type='Loan',
                    entity_id=str(row['loan_id']),
                    payload={'loan_id': str(row['loan_id'])},
                    tenant=tenant,
                )
            except Exception:
                logger.debug('Failed to emit loan.overdue for loan %s', row['loan_id'])
    except Exception:
        logger.exception('Failed to emit loan.overdue batch')
