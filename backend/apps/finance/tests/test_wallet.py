import pytest
from decimal import Decimal

from apps.saas.models import Tenant, User
from apps.finance.models import Account, Wallet
from apps.finance.constants import WalletStatus, WalletType
from apps.finance.services.wallet_service import WalletService
from core.exceptions import InsufficientFundsError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Test Lender', slug='test-lender')


@pytest.fixture
def user(db):
    return User.objects.create_user(email='borrower@example.com', password='pw')


@pytest.fixture
def cash_account(tenant):
    return Account.objects_unscoped.get(tenant=tenant, code='1000')


@pytest.fixture
def wallet(tenant, user):
    return WalletService.create_wallet(owner=user, tenant=tenant)


# ---------------------------------------------------------------------------
# create_wallet
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_wallet_returns_wallet(wallet):
    assert wallet.pk is not None
    assert wallet.balance == Decimal('0.00')
    assert wallet.status == WalletStatus.ACTIVE
    assert wallet.wallet_type == WalletType.PERSONAL


@pytest.mark.django_db
def test_create_wallet_creates_backing_account(wallet):
    assert wallet.account is not None
    assert wallet.account.pk is not None


@pytest.mark.django_db
def test_create_wallet_backing_account_is_liability(wallet):
    from apps.finance.constants import AccountType, AccountCategory
    assert wallet.account.account_type == AccountType.LIABILITY
    assert wallet.account.category == AccountCategory.BORROWER_WALLET


@pytest.mark.django_db
def test_create_wallet_unique_per_owner_type(tenant, user):
    WalletService.create_wallet(owner=user, tenant=tenant, wallet_type=WalletType.PERSONAL)
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        WalletService.create_wallet(owner=user, tenant=tenant, wallet_type=WalletType.PERSONAL)


@pytest.mark.django_db
def test_create_wallet_different_types_allowed(tenant, user):
    w1 = WalletService.create_wallet(owner=user, tenant=tenant, wallet_type=WalletType.PERSONAL)
    w2 = WalletService.create_wallet(owner=user, tenant=tenant, wallet_type=WalletType.BUSINESS)
    assert w1.pk != w2.pk


# ---------------------------------------------------------------------------
# credit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_credit_increases_stored_balance(wallet, cash_account):
    WalletService.credit(wallet, Decimal('500.00'), reference='TXN-C1', source_account=cash_account)
    wallet.refresh_from_db()
    assert wallet.balance == Decimal('500.00')


@pytest.mark.django_db
def test_credit_creates_ledger_entries(wallet, cash_account):
    from apps.finance.models import LedgerEntry
    WalletService.credit(wallet, Decimal('300.00'), reference='TXN-C2', source_account=cash_account)
    entries = LedgerEntry.objects_unscoped.filter(account=wallet.account)
    assert entries.count() == 1  # one credit entry on the wallet account


@pytest.mark.django_db
def test_credit_rejects_non_positive_amount(wallet, cash_account):
    with pytest.raises(ValueError, match="positive"):
        WalletService.credit(wallet, Decimal('0'), reference='TXN-ZERO', source_account=cash_account)


@pytest.mark.django_db
def test_credit_rejects_frozen_wallet(wallet, cash_account):
    WalletService.freeze(wallet)
    with pytest.raises(ValueError, match="frozen"):
        WalletService.credit(wallet, Decimal('100.00'), reference='TXN-F', source_account=cash_account)


@pytest.mark.django_db
def test_credit_accumulates_across_calls(wallet, cash_account):
    WalletService.credit(wallet, Decimal('100.00'), reference='TXN-A', source_account=cash_account)
    WalletService.credit(wallet, Decimal('250.00'), reference='TXN-B', source_account=cash_account)
    wallet.refresh_from_db()
    assert wallet.balance == Decimal('350.00')


# ---------------------------------------------------------------------------
# debit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_debit_decreases_stored_balance(wallet, cash_account):
    WalletService.credit(wallet, Decimal('1000.00'), reference='FUND', source_account=cash_account)
    WalletService.debit(wallet, Decimal('400.00'), reference='SPEND', destination_account=cash_account)
    wallet.refresh_from_db()
    assert wallet.balance == Decimal('600.00')


@pytest.mark.django_db
def test_debit_creates_ledger_entries(wallet, cash_account):
    from apps.finance.models import LedgerEntry
    WalletService.credit(wallet, Decimal('500.00'), reference='FUND', source_account=cash_account)
    WalletService.debit(wallet, Decimal('200.00'), reference='SPEND', destination_account=cash_account)
    entries = LedgerEntry.objects_unscoped.filter(account=wallet.account)
    # 1 credit entry + 1 debit entry
    assert entries.count() == 2


@pytest.mark.django_db
def test_debit_rejects_insufficient_funds(wallet, cash_account):
    WalletService.credit(wallet, Decimal('100.00'), reference='FUND', source_account=cash_account)
    with pytest.raises(InsufficientFundsError):
        WalletService.debit(wallet, Decimal('200.00'), reference='OVER', destination_account=cash_account)


@pytest.mark.django_db
def test_debit_rejects_non_positive_amount(wallet, cash_account):
    WalletService.credit(wallet, Decimal('100.00'), reference='FUND', source_account=cash_account)
    with pytest.raises(ValueError, match="positive"):
        WalletService.debit(wallet, Decimal('0'), reference='ZERO', destination_account=cash_account)


@pytest.mark.django_db
def test_debit_rejects_frozen_wallet(wallet, cash_account):
    WalletService.credit(wallet, Decimal('500.00'), reference='FUND', source_account=cash_account)
    WalletService.freeze(wallet)
    with pytest.raises(ValueError, match="frozen"):
        WalletService.debit(wallet, Decimal('100.00'), reference='TXN', destination_account=cash_account)


# ---------------------------------------------------------------------------
# get_balance (ledger-derived)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_balance_matches_stored_balance(wallet, cash_account):
    WalletService.credit(wallet, Decimal('750.00'), reference='TXN-1', source_account=cash_account)
    WalletService.debit(wallet, Decimal('250.00'), reference='TXN-2', destination_account=cash_account)
    wallet.refresh_from_db()
    assert WalletService.get_balance(wallet) == wallet.balance


@pytest.mark.django_db
def test_get_balance_zero_on_new_wallet(wallet):
    assert WalletService.get_balance(wallet) == Decimal('0.00')


# ---------------------------------------------------------------------------
# freeze / unfreeze
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_freeze_sets_status_to_frozen(wallet):
    WalletService.freeze(wallet)
    wallet.refresh_from_db()
    assert wallet.status == WalletStatus.FROZEN


@pytest.mark.django_db
def test_unfreeze_restores_status_to_active(wallet):
    WalletService.freeze(wallet)
    WalletService.unfreeze(wallet)
    wallet.refresh_from_db()
    assert wallet.status == WalletStatus.ACTIVE


@pytest.mark.django_db
def test_unfreeze_non_frozen_wallet_raises(wallet):
    with pytest.raises(ValueError, match="frozen"):
        WalletService.unfreeze(wallet)


@pytest.mark.django_db
def test_freeze_closed_wallet_raises(wallet):
    wallet.status = WalletStatus.CLOSED
    wallet.save()
    with pytest.raises(ValueError, match="closed"):
        WalletService.freeze(wallet)


# ---------------------------------------------------------------------------
# Ledger balance invariant preserved after wallet operations
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_ledger_balance_invariant_after_credit(tenant, wallet, cash_account):
    from apps.finance.services.ledger_service import LedgerService
    WalletService.credit(wallet, Decimal('500.00'), reference='TXN-INV', source_account=cash_account)
    assert LedgerService.validate_balance(tenant) is True


@pytest.mark.django_db
def test_ledger_balance_invariant_after_debit(tenant, wallet, cash_account):
    from apps.finance.services.ledger_service import LedgerService
    WalletService.credit(wallet, Decimal('1000.00'), reference='FUND', source_account=cash_account)
    WalletService.debit(wallet, Decimal('300.00'), reference='SPEND', destination_account=cash_account)
    assert LedgerService.validate_balance(tenant) is True


# ---------------------------------------------------------------------------
# Concurrent access safety (select_for_update re-fetch)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_debit_re_fetches_balance_before_checking(wallet, cash_account):
    """
    WalletService.debit() re-fetches the wallet with SELECT FOR UPDATE before
    checking the balance, so a stale in-memory value cannot bypass the guard.
    """
    WalletService.credit(wallet, Decimal('100.00'), reference='FUND', source_account=cash_account)

    # Simulate a stale in-memory object whose balance field was never saved
    wallet.balance = Decimal('500.00')

    # Service re-fetches from DB (actual balance = 100), so 200 is rejected
    with pytest.raises(InsufficientFundsError):
        WalletService.debit(wallet, Decimal('200.00'), reference='OVER', destination_account=cash_account)
