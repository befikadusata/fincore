from decimal import Decimal
from typing import Optional
import uuid

from django.db import transaction
from django.db.models import Sum

from apps.finance.constants import EntryType, AccountType
from apps.finance.models.account import Account
from apps.finance.models.ledger_entry import LedgerEntry


class LedgerService:
    @staticmethod
    @transaction.atomic
    def create_entry(
        debit_account: Account,
        credit_account: Account,
        amount: Decimal,
        reference: str,
        description: str = '',
        transaction_id: Optional[uuid.UUID] = None,
    ) -> tuple[LedgerEntry, LedgerEntry]:
        """Atomically creates a balanced debit + credit pair."""
        if amount <= 0:
            raise ValueError("Ledger entry amount must be positive")

        tenant = debit_account.tenant

        debit = LedgerEntry.objects_unscoped.create(
            tenant=tenant,
            account=debit_account,
            entry_type=EntryType.DEBIT,
            amount=amount,
            reference=reference,
            description=description,
            transaction_id=transaction_id,
        )
        credit = LedgerEntry.objects_unscoped.create(
            tenant=tenant,
            account=credit_account,
            entry_type=EntryType.CREDIT,
            amount=amount,
            reference=reference,
            description=description,
            transaction_id=transaction_id,
        )
        return debit, credit

    @staticmethod
    def validate_balance(tenant) -> bool:
        """Returns True when total debits equal total credits for the tenant."""
        qs = LedgerEntry.objects_unscoped.filter(tenant=tenant)
        total_debits = qs.filter(entry_type=EntryType.DEBIT).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        total_credits = qs.filter(entry_type=EntryType.CREDIT).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return total_debits == total_credits

    @staticmethod
    def get_trial_balance(tenant) -> list[dict]:
        """Returns per-account net balance aggregated from ledger entries."""
        accounts = Account.objects_unscoped.filter(tenant=tenant).prefetch_related('entries')
        result = []
        for account in accounts:
            entries = LedgerEntry.objects_unscoped.filter(
                tenant=tenant, account=account
            )
            total_debits = entries.filter(entry_type=EntryType.DEBIT).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            total_credits = entries.filter(entry_type=EntryType.CREDIT).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')

            # Net balance: debit-normal accounts (ASSET, EXPENSE) carry debit balance;
            # credit-normal accounts (LIABILITY, EQUITY, REVENUE) carry credit balance.
            if account.account_type in (AccountType.ASSET, AccountType.EXPENSE):
                net_balance = total_debits - total_credits
            else:
                net_balance = total_credits - total_debits

            result.append({
                'account_id': account.id,
                'code': account.code,
                'name': account.name,
                'account_type': account.account_type,
                'total_debits': total_debits,
                'total_credits': total_credits,
                'net_balance': net_balance,
            })
        return result
