import pytest
from datetime import date
from decimal import Decimal

from apps.saas.models import Tenant, User, Membership, Role, Permission, RolePermission
from apps.saas.services.rbac import RBACService
from apps.finance.models import Loan, LoanProduct, RepaymentSchedule, Wallet
from apps.finance.models.account import Account
from apps.finance.constants import InterestType, LoanStatus, RepaymentStatus
from apps.finance.services.loan_service import LoanService
from apps.finance.services.repayment_service import RepaymentService
from apps.finance.services.wallet_service import WalletService
from apps.finance.services.ledger_service import LedgerService
from core.exceptions import InsufficientFundsError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Test Bank', slug='test-bank')


@pytest.fixture
def borrower(db):
    return User.objects.create_user(email='borrower@bank.com', password='pw')


@pytest.fixture
def manager(db):
    return User.objects.create_user(email='manager@bank.com', password='pw')


@pytest.fixture
def flat_product(tenant):
    return LoanProduct.objects_unscoped.create(
        tenant=tenant,
        name='Flat Loan 12%',
        interest_type=InterestType.FLAT,
        interest_rate=Decimal('12.00'),
        min_term_months=3,
        max_term_months=24,
        min_amount=Decimal('1000.00'),
        max_amount=Decimal('50000.00'),
    )


@pytest.fixture
def rb_product(tenant):
    return LoanProduct.objects_unscoped.create(
        tenant=tenant,
        name='Reducing Balance 12%',
        interest_type=InterestType.REDUCING_BALANCE,
        interest_rate=Decimal('12.00'),
        min_term_months=3,
        max_term_months=24,
        min_amount=Decimal('1000.00'),
        max_amount=Decimal('50000.00'),
    )


@pytest.fixture
def setup_rbac(tenant, borrower, manager):
    perm = Permission.objects.create(codename='loans:manage', description='')
    role = Role.objects_unscoped.create(tenant=tenant, name='LoanManager', slug='loan-manager')
    RolePermission.objects.create(role=role, permission=perm)
    Membership.objects.create(tenant=tenant, user=borrower, status='active')
    Membership.objects.create(tenant=tenant, user=manager, status='active')
    RBACService.assign_role(manager, tenant, role)


@pytest.fixture
def disbursed_loan(tenant, borrower, manager, flat_product, setup_rbac):
    """12,000 ETB / 12% flat / 12 months → 1,440 interest → 1,120/month payment."""
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('12000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, manager)
    LoanService.disburse_loan(loan)  # also generates schedule + creates wallet
    return loan


@pytest.fixture
def topped_up_wallet(disbursed_loan, tenant, borrower):
    """Credit extra ETB to the wallet so the borrower can repay principal + interest."""
    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    cash = Account.objects_unscoped.get(tenant=tenant, code='1000')
    WalletService.credit(wallet, Decimal('1440.00'), 'TOP-UP', source_account=cash)
    return wallet


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
# generate_schedule
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_generate_schedule_creates_correct_count(disbursed_loan):
    count = RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).count()
    assert count == 12


@pytest.mark.django_db
def test_generate_schedule_flat_amounts(disbursed_loan):
    rows = list(RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).order_by('installment_number'))
    # 12,000 flat 12% / 12 months → principal=1000, interest=120, payment=1120 per installment
    assert rows[0].principal_amount == Decimal('1000.00')
    assert rows[0].interest_amount == Decimal('120.00')
    assert rows[0].total_amount == Decimal('1120.00')
    assert rows[0].status == RepaymentStatus.PENDING


@pytest.mark.django_db
def test_generate_schedule_due_dates_are_monthly(disbursed_loan):
    rows = list(RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).order_by('installment_number'))
    for i in range(len(rows) - 1):
        gap_months = (rows[i + 1].due_date.year - rows[i].due_date.year) * 12 + \
                     (rows[i + 1].due_date.month - rows[i].due_date.month)
        assert gap_months == 1


@pytest.mark.django_db
def test_generate_schedule_reducing_balance_decreasing_interest(tenant, borrower, manager, rb_product, setup_rbac):
    loan = LoanService.create_loan(
        product=rb_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('10000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, manager)
    LoanService.disburse_loan(loan)

    rows = list(RepaymentSchedule.objects_unscoped.filter(loan=loan).order_by('installment_number'))
    assert rows[0].interest_amount > rows[-1].interest_amount


@pytest.mark.django_db
def test_generate_schedule_is_idempotent(disbursed_loan):
    first_ids = list(
        RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).values_list('id', flat=True)
    )
    RepaymentService.generate_schedule(disbursed_loan)
    second_ids = list(
        RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).values_list('id', flat=True)
    )
    assert set(first_ids) != set(second_ids)  # new PKs, same count
    assert len(second_ids) == 12


# ---------------------------------------------------------------------------
# process_repayment
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_process_repayment_marks_installment_paid(disbursed_loan, topped_up_wallet):
    # Pay exactly one installment (1120)
    RepaymentService.process_repayment(disbursed_loan, Decimal('1120.00'))
    first = RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).order_by('installment_number').first()
    assert first.status == RepaymentStatus.PAID
    assert first.amount_paid == Decimal('1120.00')
    assert first.paid_at is not None


@pytest.mark.django_db
def test_process_repayment_partial_payment(disbursed_loan, topped_up_wallet):
    RepaymentService.process_repayment(disbursed_loan, Decimal('500.00'))
    first = RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).order_by('installment_number').first()
    assert first.status == RepaymentStatus.PARTIAL
    assert first.amount_paid == Decimal('500.00')


@pytest.mark.django_db
def test_process_repayment_spans_multiple_installments(disbursed_loan, topped_up_wallet):
    # Pay 3 installments at once (3 × 1120 = 3360)
    RepaymentService.process_repayment(disbursed_loan, Decimal('3360.00'))
    paid = RepaymentSchedule.objects_unscoped.filter(
        loan=disbursed_loan, status=RepaymentStatus.PAID
    ).count()
    assert paid == 3


@pytest.mark.django_db
def test_process_repayment_reduces_outstanding_balance(disbursed_loan, topped_up_wallet):
    before = disbursed_loan.outstanding_balance
    RepaymentService.process_repayment(disbursed_loan, Decimal('1120.00'))
    disbursed_loan.refresh_from_db()
    assert disbursed_loan.outstanding_balance == before - Decimal('1120.00')


@pytest.mark.django_db
def test_process_repayment_completes_loan(disbursed_loan, topped_up_wallet):
    # Full repayment in one shot (13,440 total)
    RepaymentService.process_repayment(disbursed_loan, Decimal('13440.00'))
    disbursed_loan.refresh_from_db()
    assert disbursed_loan.status == LoanStatus.COMPLETED
    assert disbursed_loan.completed_at is not None
    assert disbursed_loan.outstanding_balance == Decimal('0.00')


@pytest.mark.django_db
def test_process_repayment_ledger_invariant(disbursed_loan, topped_up_wallet, tenant):
    RepaymentService.process_repayment(disbursed_loan, Decimal('1120.00'))
    assert LedgerService.validate_balance(tenant) is True


@pytest.mark.django_db
def test_process_repayment_idempotency(disbursed_loan, topped_up_wallet):
    txn1 = RepaymentService.process_repayment(disbursed_loan, Decimal('1120.00'), idempotency_key='pay-001')
    txn2 = RepaymentService.process_repayment(disbursed_loan, Decimal('1120.00'), idempotency_key='pay-001')
    assert txn1.pk == txn2.pk
    # Only one installment should be paid, not two
    paid = RepaymentSchedule.objects_unscoped.filter(
        loan=disbursed_loan, status=RepaymentStatus.PAID
    ).count()
    assert paid == 1


@pytest.mark.django_db
def test_process_repayment_insufficient_funds_raises(disbursed_loan):
    # Wallet has exactly 12,000 (disbursement amount), try to repay 13,440
    with pytest.raises(InsufficientFundsError):
        RepaymentService.process_repayment(disbursed_loan, Decimal('13440.00'))


@pytest.mark.django_db
def test_process_repayment_non_active_loan_raises(tenant, borrower, manager, flat_product, setup_rbac):
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=6,
    )
    with pytest.raises(ValueError, match="Cannot repay"):
        RepaymentService.process_repayment(loan, Decimal('500.00'))


# ---------------------------------------------------------------------------
# check_overdue
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_check_overdue_marks_past_due_installments(disbursed_loan):
    # Force first two installments to a past due date
    rows = list(RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).order_by('installment_number')[:2])
    for row in rows:
        row.due_date = date(2020, 1, 1)
        row.save(update_fields=['due_date'])

    count = RepaymentService.check_overdue()
    assert count == 2

    rows[0].refresh_from_db()
    rows[1].refresh_from_db()
    assert rows[0].status == RepaymentStatus.OVERDUE
    assert rows[1].status == RepaymentStatus.OVERDUE


@pytest.mark.django_db
def test_check_overdue_does_not_affect_paid_installments(disbursed_loan, topped_up_wallet):
    # Pay first installment, then backdate it
    RepaymentService.process_repayment(disbursed_loan, Decimal('1120.00'))
    first = RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).order_by('installment_number').first()
    first.due_date = date(2020, 1, 1)
    first.save(update_fields=['due_date'])

    count = RepaymentService.check_overdue()
    first.refresh_from_db()
    assert first.status == RepaymentStatus.PAID  # unchanged


@pytest.mark.django_db
def test_check_overdue_future_installments_unaffected(disbursed_loan):
    count = RepaymentService.check_overdue()
    assert count == 0
    pending = RepaymentSchedule.objects_unscoped.filter(
        loan=disbursed_loan, status=RepaymentStatus.PENDING
    ).count()
    assert pending == 12


# ---------------------------------------------------------------------------
# apply_penalty
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_apply_penalty_adds_penalty_amount(disbursed_loan):
    inst = RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).first()
    inst.status = RepaymentStatus.OVERDUE
    inst.save(update_fields=['status'])

    updated = RepaymentService.apply_penalty(inst, penalty_amount=Decimal('50.00'))
    assert updated.penalty_amount == Decimal('50.00')


@pytest.mark.django_db
def test_apply_penalty_uses_product_config(disbursed_loan, flat_product):
    flat_product.fees_config = {'penalty_rate_pct': 2.0}
    flat_product.save(update_fields=['fees_config'])

    inst = RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).first()
    inst.status = RepaymentStatus.OVERDUE
    inst.save(update_fields=['status'])

    updated = RepaymentService.apply_penalty(inst)
    # 2% of 1120 = 22.40
    assert updated.penalty_amount == Decimal('22.40')


@pytest.mark.django_db
def test_apply_penalty_non_overdue_raises(disbursed_loan):
    inst = RepaymentSchedule.objects_unscoped.filter(loan=disbursed_loan).first()
    assert inst.status == RepaymentStatus.PENDING
    with pytest.raises(ValueError, match="overdue"):
        RepaymentService.apply_penalty(inst, penalty_amount=Decimal('10.00'))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_api_repay_loan(api_client, disbursed_loan, topped_up_wallet, setup_rbac, borrower):
    _auth(api_client, borrower)
    response = api_client.post(
        f'/api/v1/finance/loans/{disbursed_loan.pk}/repay/',
        {'amount': '1120.00'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['status'] == 'completed'
    assert Decimal(response.data['amount']) == Decimal('1120.00')


@pytest.mark.django_db
def test_api_repay_partial(api_client, disbursed_loan, topped_up_wallet, setup_rbac, borrower):
    _auth(api_client, borrower)
    response = api_client.post(
        f'/api/v1/finance/loans/{disbursed_loan.pk}/repay/',
        {'amount': '600.00'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['loan_status'] == 'active'


@pytest.mark.django_db
def test_api_schedule_returns_persisted_data(api_client, disbursed_loan, setup_rbac, borrower):
    _auth(api_client, borrower)
    response = api_client.get(f'/api/v1/finance/loans/{disbursed_loan.pk}/schedule/')
    assert response.status_code == 200
    assert len(response.data['installments']) == 12
    # Persisted schedule has status field
    assert 'status' in response.data['installments'][0]
    assert response.data['installments'][0]['status'] == 'pending'


@pytest.mark.django_db
def test_api_repay_full_loan_completes_it(api_client, disbursed_loan, topped_up_wallet, setup_rbac, borrower):
    _auth(api_client, borrower)
    response = api_client.post(
        f'/api/v1/finance/loans/{disbursed_loan.pk}/repay/',
        {'amount': '13440.00'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['loan_status'] == 'completed'
    assert Decimal(response.data['outstanding_balance']) == Decimal('0.00')
