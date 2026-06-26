from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import Count, Q, Sum

from apps.finance.constants import EntryType, LoanStatus, RepaymentStatus
from apps.finance.models.ledger_entry import LedgerEntry
from apps.finance.models.repayment_schedule import RepaymentSchedule
from apps.finance.models.wallet import Wallet
from apps.finance.services.ledger_service import LedgerService


class ReportingService:
    @staticmethod
    def get_trial_balance(tenant) -> dict:
        rows = LedgerService.get_trial_balance(tenant)
        total_debits = sum(r['total_debits'] for r in rows)
        total_credits = sum(r['total_credits'] for r in rows)
        return {
            'accounts': rows,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'balanced': total_debits == total_credits,
        }

    @staticmethod
    def get_loan_summary(tenant) -> dict:
        from apps.finance.models.loan import Loan

        agg = Loan.objects_unscoped.filter(tenant=tenant).aggregate(
            active_count=Count('pk', filter=Q(status=LoanStatus.ACTIVE)),
            completed_count=Count('pk', filter=Q(status=LoanStatus.COMPLETED)),
            defaulted_count=Count('pk', filter=Q(status=LoanStatus.DEFAULTED)),
            total_outstanding=Sum(
                'outstanding_balance', filter=Q(status=LoanStatus.ACTIVE)
            ),
            total_disbursed=Sum(
                'principal_amount',
                filter=Q(status__in=[
                    LoanStatus.DISBURSED, LoanStatus.ACTIVE,
                    LoanStatus.COMPLETED, LoanStatus.DEFAULTED,
                ]),
            ),
        )

        overdue_count = RepaymentSchedule.objects_unscoped.filter(
            tenant=tenant, status=RepaymentStatus.OVERDUE
        ).count()

        return {
            'active_count': agg['active_count'],
            'completed_count': agg['completed_count'],
            'defaulted_count': agg['defaulted_count'],
            'total_outstanding': agg['total_outstanding'] or Decimal('0'),
            'total_disbursed': agg['total_disbursed'] or Decimal('0'),
            'overdue_installments': overdue_count,
        }

    @staticmethod
    def get_wallet_statement(
        wallet: Wallet,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        all_entries = LedgerEntry.objects_unscoped.filter(account=wallet.account)

        # Opening balance: sum of all entries strictly before start_date
        if start_date:
            before = all_entries.filter(created_at__date__lt=start_date)
            credits_before = before.filter(entry_type=EntryType.CREDIT).aggregate(
                s=Sum('amount')
            )['s'] or Decimal('0')
            debits_before = before.filter(entry_type=EntryType.DEBIT).aggregate(
                s=Sum('amount')
            )['s'] or Decimal('0')
            opening_balance = credits_before - debits_before  # LIABILITY: credit-normal
        else:
            opening_balance = Decimal('0')

        # Period entries
        period_qs = all_entries
        if start_date:
            period_qs = period_qs.filter(created_at__date__gte=start_date)
        if end_date:
            period_qs = period_qs.filter(created_at__date__lte=end_date)
        period_qs = period_qs.order_by('created_at')

        entries = []
        running = opening_balance
        for entry in period_qs:
            if entry.entry_type == EntryType.CREDIT:
                running += entry.amount
            else:
                running -= entry.amount
            entries.append({
                'id': str(entry.id),
                'created_at': entry.created_at.isoformat(),
                'entry_type': entry.entry_type,
                'amount': str(entry.amount),
                'reference': entry.reference,
                'description': entry.description,
                'balance_after': str(running),
            })

        return {
            'wallet_id': str(wallet.id),
            'currency': wallet.currency,
            'opening_balance': str(opening_balance),
            'closing_balance': str(running if entries else opening_balance),
            'entries': entries,
        }
