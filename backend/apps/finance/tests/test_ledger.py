import pytest
from decimal import Decimal

from apps.saas.models import Tenant
from apps.finance.models import Account, LedgerEntry
from apps.finance.constants import AccountType, AccountCategory, EntryType
from apps.finance.services.ledger_service import LedgerService
from apps.finance.signals import SYSTEM_CHART_OF_ACCOUNTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    # post_save signal fires here and creates the chart of accounts
    return Tenant.objects.create(name='Test Lender', slug='test-lender')


@pytest.fixture
def cash_account(tenant):
    return Account.objects_unscoped.get(tenant=tenant, code='1000')


@pytest.fixture
def interest_revenue_account(tenant):
    return Account.objects_unscoped.get(tenant=tenant, code='4000')


@pytest.fixture
def loan_receivable_account(tenant):
    return Account.objects_unscoped.get(tenant=tenant, code='1100')


# ---------------------------------------------------------------------------
# System account creation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_system_accounts_created_on_tenant_creation(tenant):
    accounts = Account.objects_unscoped.filter(tenant=tenant)
    assert accounts.count() == len(SYSTEM_CHART_OF_ACCOUNTS)
    codes = set(accounts.values_list('code', flat=True))
    expected = {row[0] for row in SYSTEM_CHART_OF_ACCOUNTS}
    assert codes == expected


@pytest.mark.django_db
def test_system_accounts_are_flagged_is_system(tenant):
    non_system = Account.objects_unscoped.filter(tenant=tenant, is_system=False)
    assert non_system.count() == 0


@pytest.mark.django_db
def test_system_accounts_isolated_between_tenants(db):
    t1 = Tenant.objects.create(name='Lender A', slug='lender-a')
    t2 = Tenant.objects.create(name='Lender B', slug='lender-b')

    t1_accounts = Account.objects_unscoped.filter(tenant=t1)
    t2_accounts = Account.objects_unscoped.filter(tenant=t2)

    assert t1_accounts.count() == len(SYSTEM_CHART_OF_ACCOUNTS)
    assert t2_accounts.count() == len(SYSTEM_CHART_OF_ACCOUNTS)
    # No cross-tenant overlap
    assert not t1_accounts.filter(tenant=t2).exists()


# ---------------------------------------------------------------------------
# Double-entry creation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_entry_creates_debit_and_credit_rows(cash_account, interest_revenue_account):
    debit, credit = LedgerService.create_entry(
        debit_account=cash_account,
        credit_account=interest_revenue_account,
        amount=Decimal('500.00'),
        reference='TXN-001',
    )

    assert debit.entry_type == EntryType.DEBIT
    assert credit.entry_type == EntryType.CREDIT
    assert debit.amount == Decimal('500.00')
    assert credit.amount == Decimal('500.00')
    assert debit.account == cash_account
    assert credit.account == interest_revenue_account


@pytest.mark.django_db
def test_create_entry_same_tenant_on_both_rows(cash_account, interest_revenue_account):
    debit, credit = LedgerService.create_entry(
        debit_account=cash_account,
        credit_account=interest_revenue_account,
        amount=Decimal('100.00'),
        reference='TXN-002',
    )
    assert debit.tenant_id == credit.tenant_id == cash_account.tenant_id


@pytest.mark.django_db
def test_create_entry_rejects_non_positive_amount(cash_account, interest_revenue_account):
    with pytest.raises(ValueError, match="must be positive"):
        LedgerService.create_entry(
            debit_account=cash_account,
            credit_account=interest_revenue_account,
            amount=Decimal('0'),
            reference='TXN-ZERO',
        )


@pytest.mark.django_db
def test_create_entry_stores_transaction_id(cash_account, interest_revenue_account):
    import uuid
    txn_id = uuid.uuid4()
    debit, credit = LedgerService.create_entry(
        debit_account=cash_account,
        credit_account=interest_revenue_account,
        amount=Decimal('250.00'),
        reference='TXN-003',
        transaction_id=txn_id,
    )
    assert debit.transaction_id == txn_id
    assert credit.transaction_id == txn_id


# ---------------------------------------------------------------------------
# Balance invariant
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_validate_balance_true_after_entries(
    tenant, cash_account, interest_revenue_account, loan_receivable_account
):
    LedgerService.create_entry(cash_account, interest_revenue_account, Decimal('1000.00'), 'TXN-A')
    LedgerService.create_entry(loan_receivable_account, cash_account, Decimal('2000.00'), 'TXN-B')

    assert LedgerService.validate_balance(tenant) is True


@pytest.mark.django_db
def test_validate_balance_true_on_empty_ledger(tenant):
    assert LedgerService.validate_balance(tenant) is True


@pytest.mark.django_db
def test_validate_balance_false_when_orphan_entry_exists(tenant, cash_account):
    # Bypass the service to manually insert an unbalanced entry
    LedgerEntry.objects_unscoped.create(
        tenant=tenant,
        account=cash_account,
        entry_type=EntryType.DEBIT,
        amount=Decimal('999.00'),
        reference='ORPHAN',
    )
    assert LedgerService.validate_balance(tenant) is False


@pytest.mark.django_db
def test_validate_balance_isolated_per_tenant(db):
    t1 = Tenant.objects.create(name='Lender A', slug='lender-a')
    t2 = Tenant.objects.create(name='Lender B', slug='lender-b')

    cash_t1 = Account.objects_unscoped.get(tenant=t1, code='1000')
    rev_t1 = Account.objects_unscoped.get(tenant=t1, code='4000')
    LedgerService.create_entry(cash_t1, rev_t1, Decimal('500.00'), 'TXN-T1')

    # Inject an orphan into t2 only
    cash_t2 = Account.objects_unscoped.get(tenant=t2, code='1000')
    LedgerEntry.objects_unscoped.create(
        tenant=t2, account=cash_t2,
        entry_type=EntryType.DEBIT,
        amount=Decimal('100.00'),
        reference='ORPHAN-T2',
    )

    assert LedgerService.validate_balance(t1) is True
    assert LedgerService.validate_balance(t2) is False


# ---------------------------------------------------------------------------
# Trial balance
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_trial_balance_returns_all_accounts(tenant):
    result = LedgerService.get_trial_balance(tenant)
    assert len(result) == len(SYSTEM_CHART_OF_ACCOUNTS)


@pytest.mark.django_db
def test_trial_balance_zero_when_no_entries(tenant):
    result = LedgerService.get_trial_balance(tenant)
    for row in result:
        assert row['total_debits'] == Decimal('0')
        assert row['total_credits'] == Decimal('0')
        assert row['net_balance'] == Decimal('0')


@pytest.mark.django_db
def test_trial_balance_accuracy(tenant, cash_account, interest_revenue_account):
    LedgerService.create_entry(cash_account, interest_revenue_account, Decimal('1500.00'), 'TXN-X')

    result = LedgerService.get_trial_balance(tenant)
    by_code = {row['code']: row for row in result}

    # Cash (ASSET): debit increases it → net = debit - credit = 1500
    assert by_code['1000']['total_debits'] == Decimal('1500.00')
    assert by_code['1000']['total_credits'] == Decimal('0')
    assert by_code['1000']['net_balance'] == Decimal('1500.00')

    # Interest Revenue (REVENUE): credit increases it → net = credit - debit = 1500
    assert by_code['4000']['total_credits'] == Decimal('1500.00')
    assert by_code['4000']['total_debits'] == Decimal('0')
    assert by_code['4000']['net_balance'] == Decimal('1500.00')


@pytest.mark.django_db
def test_trial_balance_multiple_entries_accumulate(
    tenant, cash_account, interest_revenue_account, loan_receivable_account
):
    LedgerService.create_entry(cash_account, interest_revenue_account, Decimal('1000.00'), 'TXN-1')
    LedgerService.create_entry(loan_receivable_account, cash_account, Decimal('400.00'), 'TXN-2')

    result = LedgerService.get_trial_balance(tenant)
    by_code = {row['code']: row for row in result}

    # Cash: +1000 debit, -400 debit credited away → net = 1000 - 400 = 600
    assert by_code['1000']['total_debits'] == Decimal('1000.00')
    assert by_code['1000']['total_credits'] == Decimal('400.00')
    assert by_code['1000']['net_balance'] == Decimal('600.00')

    # Loan Receivable (ASSET): +400 debit → net = 400
    assert by_code['1100']['total_debits'] == Decimal('400.00')
    assert by_code['1100']['net_balance'] == Decimal('400.00')
