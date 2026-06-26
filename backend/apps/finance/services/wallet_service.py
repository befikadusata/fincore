from decimal import Decimal
from typing import Optional
import uuid

from django.db import transaction
from django.db.models import Sum

from apps.finance.constants import (
    AccountType,
    AccountCategory,
    EntryType,
    WalletStatus,
    WalletType,
)
from apps.finance.models.account import Account
from apps.finance.models.ledger_entry import LedgerEntry
from apps.finance.models.wallet import Wallet
from apps.finance.services.ledger_service import LedgerService
from core.exceptions import InsufficientFundsError


class WalletService:
    @staticmethod
    @transaction.atomic
    def create_wallet(
        owner,
        tenant,
        wallet_type: str = WalletType.PERSONAL,
        currency: str = 'ETB',
    ) -> Wallet:
        short_id = str(uuid.uuid4()).replace('-', '')[:8].upper()
        account = Account.objects_unscoped.create(
            tenant=tenant,
            code=f'W-{short_id}',
            name=f'Wallet ({wallet_type}) — {owner.email}',
            account_type=AccountType.LIABILITY,
            category=AccountCategory.BORROWER_WALLET,
            is_system=False,
        )
        wallet = Wallet.objects_unscoped.create(
            tenant=tenant,
            owner=owner,
            account=account,
            wallet_type=wallet_type,
            currency=currency,
        )
        return wallet

    @staticmethod
    @transaction.atomic
    def credit(
        wallet: Wallet,
        amount: Decimal,
        reference: str,
        source_account: Optional[Account] = None,
        transaction_id: Optional[uuid.UUID] = None,
    ) -> Wallet:
        """Increase wallet balance. source_account defaults to tenant Cash account."""
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        if wallet.status != WalletStatus.ACTIVE:
            raise ValueError(f"Cannot credit a {wallet.status} wallet")

        if source_account is None:
            source_account = Account.objects_unscoped.get(
                tenant_id=wallet.tenant_id, code='1000'
            )

        # Wallet account is LIABILITY (credit-normal): CR increases balance
        LedgerService.create_entry(
            debit_account=source_account,
            credit_account=wallet.account,
            amount=amount,
            reference=reference,
            transaction_id=transaction_id,
        )

        wallet.balance += amount
        wallet.save(update_fields=['balance', 'updated_at'])
        return wallet

    @staticmethod
    @transaction.atomic
    def debit(
        wallet: Wallet,
        amount: Decimal,
        reference: str,
        destination_account: Optional[Account] = None,
        transaction_id: Optional[uuid.UUID] = None,
    ) -> Wallet:
        """Decrease wallet balance. destination_account defaults to tenant Cash account."""
        if amount <= 0:
            raise ValueError("Debit amount must be positive")

        # Re-fetch with a row lock so concurrent debits see the latest balance
        wallet = Wallet.objects_unscoped.select_for_update().get(pk=wallet.pk)

        if wallet.status != WalletStatus.ACTIVE:
            raise ValueError(f"Cannot debit a {wallet.status} wallet")

        if wallet.balance < amount:
            raise InsufficientFundsError(
                details={'available': str(wallet.balance), 'requested': str(amount)}
            )

        if destination_account is None:
            destination_account = Account.objects_unscoped.get(
                tenant_id=wallet.tenant_id, code='1000'
            )

        # Wallet account is LIABILITY: DR reduces the balance
        LedgerService.create_entry(
            debit_account=wallet.account,
            credit_account=destination_account,
            amount=amount,
            reference=reference,
            transaction_id=transaction_id,
        )

        wallet.balance -= amount
        wallet.save(update_fields=['balance', 'updated_at'])
        return wallet

    @staticmethod
    def get_balance(wallet: Wallet) -> Decimal:
        """Recalculate balance from ledger entries (for reconciliation)."""
        entries = LedgerEntry.objects_unscoped.filter(account=wallet.account)
        total_credits = entries.filter(entry_type=EntryType.CREDIT).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        total_debits = entries.filter(entry_type=EntryType.DEBIT).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        # LIABILITY account: balance = credits − debits
        return total_credits - total_debits

    @staticmethod
    def freeze(wallet: Wallet) -> Wallet:
        if wallet.status == WalletStatus.CLOSED:
            raise ValueError("Cannot freeze a closed wallet")
        wallet.status = WalletStatus.FROZEN
        wallet.save(update_fields=['status', 'updated_at'])
        return wallet

    @staticmethod
    def unfreeze(wallet: Wallet) -> Wallet:
        if wallet.status != WalletStatus.FROZEN:
            raise ValueError("Only frozen wallets can be unfrozen")
        wallet.status = WalletStatus.ACTIVE
        wallet.save(update_fields=['status', 'updated_at'])
        return wallet
