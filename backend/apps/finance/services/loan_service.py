import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.finance.constants import (
    InterestType,
    LoanStatus,
    TransactionType,
    TransactionStatus,
)
from apps.finance.models.account import Account
from apps.finance.models.loan_product import LoanProduct
from apps.finance.models.wallet import Wallet
from apps.finance.services.interest import InterestCalculatorFactory
from apps.finance.services.wallet_service import WalletService
from apps.finance.state_machines.loan_state_machine import loan_state_machine

logger = logging.getLogger(__name__)


def _emit_loan_event(event_type: str, loan) -> None:
    try:
        from apps.events.constants import EventType  # noqa: F401
        from apps.events.services.event_bus import EventBus
        EventBus.emit(
            event_type=event_type,
            entity_type='Loan',
            entity_id=str(loan.pk),
            payload={
                'loan_id': str(loan.pk),
                'status': loan.status,
                'borrower_id': str(loan.borrower_id),
                'principal_amount': str(loan.principal_amount),
            },
            tenant=loan.tenant,
        )
    except Exception:
        logger.debug('Failed to emit %s for loan %s', event_type, loan.pk)


class LoanService:
    @staticmethod
    @transaction.atomic
    def create_loan(
        product: LoanProduct,
        borrower,
        tenant,
        principal_amount: Decimal,
        term_months: int,
        idempotency_key: str = '',
        notes: str = '',
    ):
        from apps.finance.models.loan import Loan

        if not product.is_active:
            raise ValueError("Loan product is not active")

        if principal_amount < product.min_amount or principal_amount > product.max_amount:
            raise ValueError(
                f"Principal must be between {product.min_amount} and {product.max_amount}"
            )

        if term_months < product.min_term_months or term_months > product.max_term_months:
            raise ValueError(
                f"Term must be between {product.min_term_months} and {product.max_term_months} months"
            )

        if idempotency_key:
            existing = Loan.objects_unscoped.filter(
                tenant=tenant, idempotency_key=idempotency_key
            ).first()
            if existing:
                return existing

        calculator = InterestCalculatorFactory.for_product(product)
        result = calculator.calculate(principal_amount, product.interest_rate, term_months)

        return Loan.objects_unscoped.create(
            tenant=tenant,
            product=product,
            borrower=borrower,
            principal_amount=principal_amount,
            interest_amount=result.total_interest,
            total_amount=result.total_repayable,
            outstanding_balance=result.total_repayable,
            term_months=term_months,
            currency=product.currency,
            idempotency_key=idempotency_key,
            notes=notes,
        )

    @staticmethod
    def submit_loan(loan):
        loan = loan_state_machine.transition(loan, 'status', LoanStatus.SUBMITTED)
        loan.submitted_at = timezone.now()
        loan.save(update_fields=['submitted_at', 'updated_at'])
        _emit_loan_event('loan.submitted', loan)
        return loan

    @staticmethod
    def approve_loan(loan, approver=None):
        if loan.status == LoanStatus.SUBMITTED:
            loan_state_machine.transition(loan, 'status', LoanStatus.UNDER_REVIEW)
        loan = loan_state_machine.transition(loan, 'status', LoanStatus.APPROVED)
        loan.approved_by = approver
        loan.approved_at = timezone.now()
        loan.save(update_fields=['approved_by', 'approved_at', 'updated_at'])
        _emit_loan_event('loan.approved', loan)
        return loan

    @staticmethod
    def reject_loan(loan):
        loan = loan_state_machine.transition(loan, 'status', LoanStatus.REJECTED)
        _emit_loan_event('loan.rejected', loan)
        return loan

    @staticmethod
    @transaction.atomic
    def disburse_loan(loan):
        from apps.finance.models.loan import Transaction

        loan_state_machine.transition(loan, 'status', LoanStatus.DISBURSED)

        wallet = Wallet.objects_unscoped.filter(
            tenant=loan.tenant, owner=loan.borrower
        ).first()
        if not wallet:
            wallet = WalletService.create_wallet(
                loan.borrower, loan.tenant, currency=loan.currency
            )

        # DR Loan Receivable (1100), CR Borrower Wallet
        loan_receivable = Account.objects_unscoped.get(tenant=loan.tenant, code='1100')
        WalletService.credit(
            wallet=wallet,
            amount=loan.principal_amount,
            reference=f'DISBURSE-{loan.pk}',
            source_account=loan_receivable,
        )

        Transaction.objects_unscoped.create(
            tenant=loan.tenant,
            loan=loan,
            wallet=wallet,
            transaction_type=TransactionType.DISBURSEMENT,
            amount=loan.principal_amount,
            status=TransactionStatus.COMPLETED,
            reference=f'DISBURSE-{loan.pk}',
        )

        loan_state_machine.transition(loan, 'status', LoanStatus.ACTIVE)
        loan.disbursed_at = timezone.now()
        loan.save(update_fields=['disbursed_at', 'updated_at'])

        # Generate repayment schedule inside the same atomic transaction
        from apps.finance.services.repayment_service import RepaymentService
        RepaymentService.generate_schedule(loan)

        _emit_loan_event('loan.disbursed', loan)
        return loan

    @staticmethod
    def default_loan(loan):
        loan = loan_state_machine.transition(loan, 'status', LoanStatus.DEFAULTED)
        _emit_loan_event('loan.defaulted', loan)
        return loan

    @staticmethod
    def compute_schedule(loan) -> dict:
        calc = InterestCalculatorFactory.for_product(loan.product)
        result = calc.calculate(loan.principal_amount, loan.product.interest_rate, loan.term_months)

        installments = []
        n = int(loan.term_months)
        r = loan.product.interest_rate / Decimal('1200')

        if loan.product.interest_type == InterestType.REDUCING_BALANCE:
            balance = loan.principal_amount
            pmt = result.monthly_payment
            for i in range(1, n + 1):
                if r == Decimal('0'):
                    interest_portion = Decimal('0')
                    principal_portion = pmt
                else:
                    interest_portion = (balance * r).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    principal_portion = (pmt - interest_portion).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                balance = max(balance - principal_portion, Decimal('0'))
                installments.append({
                    'installment': i,
                    'principal': str(principal_portion),
                    'interest': str(interest_portion),
                    'payment': str(principal_portion + interest_portion),
                    'balance': str(balance),
                })
        else:
            monthly_principal = (loan.principal_amount / n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            monthly_interest = (result.total_interest / n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            balance = loan.principal_amount
            for i in range(1, n + 1):
                balance = max(balance - monthly_principal, Decimal('0'))
                installments.append({
                    'installment': i,
                    'principal': str(monthly_principal),
                    'interest': str(monthly_interest),
                    'payment': str(monthly_principal + monthly_interest),
                    'balance': str(balance),
                })

        return {
            'loan_id': str(loan.pk),
            'principal': str(loan.principal_amount),
            'total_interest': str(result.total_interest),
            'total_repayable': str(result.total_repayable),
            'monthly_payment': str(result.monthly_payment),
            'term_months': n,
            'installments': installments,
        }
