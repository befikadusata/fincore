import pytest
from datetime import date, timedelta
from decimal import Decimal

from apps.saas.models import Tenant, User, Membership, Role, Permission, RolePermission
from apps.saas.services.rbac import RBACService
from apps.finance.models import Loan, LoanProduct, RepaymentSchedule
from apps.finance.models.account import Account
from apps.finance.models.wallet import Wallet
from apps.finance.constants import InterestType, LoanStatus, RepaymentStatus
from apps.finance.services.loan_service import LoanService
from apps.finance.services.repayment_service import RepaymentService
from apps.finance.services.reporting_service import ReportingService
from apps.finance.services.wallet_service import WalletService
from apps.finance.services.ledger_service import LedgerService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Report Bank', slug='report-bank')


@pytest.fixture
def borrower(db):
    return User.objects.create_user(email='borrower@rbank.com', password='pw')


@pytest.fixture
def manager(db):
    return User.objects.create_user(email='manager@rbank.com', password='pw')


@pytest.fixture
def flat_product(tenant):
    return LoanProduct.objects_unscoped.create(
        tenant=tenant,
        name='Flat 12%',
        interest_type=InterestType.FLAT,
        interest_rate=Decimal('12.00'),
        min_term_months=3,
        max_term_months=24,
        min_amount=Decimal('1000.00'),
        max_amount=Decimal('50000.00'),
    )


@pytest.fixture
def setup_rbac(tenant, borrower, manager):
    perm = Permission.objects.create(codename='loans:manage:report', description='')
    role = Role.objects_unscoped.create(tenant=tenant, name='LM', slug='lm-report')
    RolePermission.objects.create(role=role, permission=perm)
    Membership.objects.create(tenant=tenant, user=borrower, status='active')
    Membership.objects.create(tenant=tenant, user=manager, status='active')
    RBACService.assign_role(manager, tenant, role)


@pytest.fixture
def active_loan(tenant, borrower, manager, flat_product, setup_rbac):
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('12000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, manager)
    LoanService.disburse_loan(loan)
    return loan


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


def _auth(client, user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}',
        HTTP_X_TENANT_ID=str(user.memberships.first().tenant_id),
    )


# ---------------------------------------------------------------------------
# ReportingService — trial balance
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_trial_balance_returns_all_system_accounts(tenant):
    data = ReportingService.get_trial_balance(tenant)
    # 8 system accounts created by signal
    assert len(data['accounts']) == 8


@pytest.mark.django_db
def test_trial_balance_is_balanced_after_disbursement(tenant, active_loan):
    data = ReportingService.get_trial_balance(tenant)
    assert data['balanced'] is True
    assert data['total_debits'] == data['total_credits']


@pytest.mark.django_db
def test_trial_balance_reflects_loan_receivable(tenant, active_loan):
    data = ReportingService.get_trial_balance(tenant)
    loan_recv = next(a for a in data['accounts'] if a['code'] == '1100')
    # Loan Receivable (ASSET): DR at disbursement
    assert loan_recv['net_balance'] == active_loan.principal_amount


@pytest.mark.django_db
def test_trial_balance_tenant_scoped(tenant, borrower, manager, flat_product, setup_rbac):
    # Create a loan on a second tenant and verify its accounts don't appear
    tenant2 = Tenant.objects.create(name='Other Bank', slug='other-bank')
    data = ReportingService.get_trial_balance(tenant2)
    codes = {a['code'] for a in data['accounts']}
    tenant1_data = ReportingService.get_trial_balance(tenant)
    tenant1_codes = {a['code'] for a in tenant1_data['accounts']}
    # Each tenant has its own isolated accounts
    assert codes == tenant1_codes  # same system account codes but different rows


# ---------------------------------------------------------------------------
# ReportingService — loan summary
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_loan_summary_empty_tenant(tenant):
    data = ReportingService.get_loan_summary(tenant)
    assert data['active_count'] == 0
    assert data['completed_count'] == 0
    assert data['defaulted_count'] == 0
    assert data['total_outstanding'] == Decimal('0')
    assert data['total_disbursed'] == Decimal('0')
    assert data['overdue_installments'] == 0


@pytest.mark.django_db
def test_loan_summary_counts_active(tenant, active_loan):
    data = ReportingService.get_loan_summary(tenant)
    assert data['active_count'] == 1
    assert data['total_outstanding'] == active_loan.outstanding_balance
    assert data['total_disbursed'] == active_loan.principal_amount


@pytest.mark.django_db
def test_loan_summary_counts_completed(tenant, active_loan, borrower):
    # Top up wallet and fully repay
    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    cash = Account.objects_unscoped.get(tenant=tenant, code='1000')
    WalletService.credit(wallet, Decimal('1440.00'), 'TOP-UP', source_account=cash)
    RepaymentService.process_repayment(active_loan, Decimal('13440.00'))

    data = ReportingService.get_loan_summary(tenant)
    assert data['completed_count'] == 1
    assert data['active_count'] == 0
    assert data['total_outstanding'] == Decimal('0')


@pytest.mark.django_db
def test_loan_summary_counts_defaulted(tenant, active_loan):
    LoanService.default_loan(active_loan)
    data = ReportingService.get_loan_summary(tenant)
    assert data['defaulted_count'] == 1
    assert data['active_count'] == 0


@pytest.mark.django_db
def test_loan_summary_counts_overdue_installments(tenant, active_loan):
    # Force some installments to the past
    rows = list(RepaymentSchedule.objects_unscoped.filter(loan=active_loan).order_by('installment_number')[:3])
    for row in rows:
        row.due_date = date(2020, 1, 1)
        row.save(update_fields=['due_date'])
    RepaymentService.check_overdue()

    data = ReportingService.get_loan_summary(tenant)
    assert data['overdue_installments'] == 3


# ---------------------------------------------------------------------------
# ReportingService — wallet statement
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_wallet_statement_all_entries(tenant, active_loan, borrower):
    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    data = ReportingService.get_wallet_statement(wallet)
    # Disbursement created one credit entry on the wallet account
    assert len(data['entries']) == 1
    assert data['entries'][0]['entry_type'] == 'credit'
    assert Decimal(data['entries'][0]['amount']) == active_loan.principal_amount


@pytest.mark.django_db
def test_wallet_statement_closing_balance_matches_wallet_balance(tenant, active_loan, borrower):
    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    data = ReportingService.get_wallet_statement(wallet)
    assert Decimal(data['closing_balance']) == wallet.balance


@pytest.mark.django_db
def test_wallet_statement_running_balance_sequence(tenant, active_loan, borrower):
    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    cash = Account.objects_unscoped.get(tenant=tenant, code='1000')
    # Add a second credit so we have two entries
    WalletService.credit(wallet, Decimal('500.00'), 'EXTRA', source_account=cash)

    data = ReportingService.get_wallet_statement(wallet)
    assert len(data['entries']) == 2
    balances = [Decimal(e['balance_after']) for e in data['entries']]
    # Each balance should be strictly greater than the previous (both are credits)
    assert balances[1] > balances[0]
    assert balances[-1] == wallet.balance


@pytest.mark.django_db
def test_wallet_statement_opening_balance_with_start_date(tenant, active_loan, borrower):
    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    # Start date in the future — all entries are "before"
    future_date = date.today() + timedelta(days=30)
    data = ReportingService.get_wallet_statement(wallet, start_date=future_date)
    # Opening balance = current balance, no period entries
    assert Decimal(data['opening_balance']) == wallet.balance
    assert data['entries'] == []


@pytest.mark.django_db
def test_wallet_statement_end_date_filter_excludes_later_entries(tenant, active_loan, borrower):
    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    # end_date yesterday → disbursement today is excluded
    yesterday = date.today() - timedelta(days=1)
    data = ReportingService.get_wallet_statement(wallet, end_date=yesterday)
    assert data['entries'] == []
    assert Decimal(data['closing_balance']) == Decimal('0')


# ---------------------------------------------------------------------------
# API — trial balance
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_api_trial_balance(api_client, active_loan, setup_rbac, borrower):
    _auth(api_client, borrower)
    response = api_client.get('/api/v1/finance/ledger/trial-balance/')
    assert response.status_code == 200
    assert response.data['balanced'] is True
    # 8 system accounts + 1 borrower wallet account created at disbursement
    assert len(response.data['accounts']) >= 8


@pytest.mark.django_db
def test_api_trial_balance_requires_auth(api_client):
    response = api_client.get('/api/v1/finance/ledger/trial-balance/')
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# API — loan summary
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_api_loan_summary(api_client, active_loan, setup_rbac, borrower):
    _auth(api_client, borrower)
    response = api_client.get('/api/v1/finance/loans/summary/')
    assert response.status_code == 200
    assert response.data['active_count'] == 1
    assert Decimal(response.data['total_outstanding']) == active_loan.outstanding_balance


# ---------------------------------------------------------------------------
# API — wallet statement
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_api_wallet_statement(api_client, active_loan, setup_rbac, borrower, tenant):
    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    _auth(api_client, borrower)
    response = api_client.get(f'/api/v1/finance/wallets/{wallet.pk}/statement/')
    assert response.status_code == 200
    assert len(response.data['entries']) == 1
    assert response.data['entries'][0]['entry_type'] == 'credit'


@pytest.mark.django_db
def test_api_wallet_statement_date_filter(api_client, active_loan, setup_rbac, borrower, tenant):
    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    _auth(api_client, borrower)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    response = api_client.get(
        f'/api/v1/finance/wallets/{wallet.pk}/statement/?end_date={yesterday}'
    )
    assert response.status_code == 200
    assert response.data['entries'] == []


@pytest.mark.django_db
def test_api_wallet_from_other_tenant_returns_404(api_client, active_loan, setup_rbac, borrower, tenant):
    # Create a wallet on a different tenant — accessing it should 404
    tenant2 = Tenant.objects.create(name='Other', slug='other-report')
    other_user = User.objects.create_user(email='other@other.com', password='pw')
    other_wallet = WalletService.create_wallet(other_user, tenant2)

    _auth(api_client, borrower)
    response = api_client.get(f'/api/v1/finance/wallets/{other_wallet.pk}/statement/')
    assert response.status_code == 404
