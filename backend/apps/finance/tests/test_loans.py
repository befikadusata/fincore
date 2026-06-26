import pytest
from decimal import Decimal

from apps.saas.models import Tenant, User, Membership, Role, Permission, RolePermission
from apps.saas.services.rbac import RBACService
from apps.finance.models import Loan, LoanProduct, Wallet
from apps.finance.constants import InterestType, LoanStatus
from apps.finance.services.loan_service import LoanService
from core.exceptions import InvalidStateTransitionError


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
        name='Flat Loan',
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
        name='Reducing Balance Loan',
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
    return {'tenant': tenant, 'borrower': borrower, 'manager': manager}


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
# LoanService — create_loan
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_loan_flat_interest(tenant, borrower, flat_product):
    loan = LoanService.create_loan(
        product=flat_product,
        borrower=borrower,
        tenant=tenant,
        principal_amount=Decimal('12000.00'),
        term_months=12,
    )
    assert loan.pk is not None
    assert loan.status == LoanStatus.CREATED
    # 12,000 × 12% × 1 year = 1,440 interest
    assert loan.interest_amount == Decimal('1440.00')
    assert loan.total_amount == Decimal('13440.00')
    assert loan.outstanding_balance == Decimal('13440.00')
    assert loan.currency == 'ETB'


@pytest.mark.django_db
def test_create_loan_reducing_balance_interest(tenant, borrower, rb_product):
    loan = LoanService.create_loan(
        product=rb_product,
        borrower=borrower,
        tenant=tenant,
        principal_amount=Decimal('10000.00'),
        term_months=12,
    )
    # Reducing balance total interest is less than flat for same rate
    assert loan.interest_amount < Decimal('1200.00')
    assert loan.total_amount == loan.principal_amount + loan.interest_amount


@pytest.mark.django_db
def test_create_loan_rejects_inactive_product(tenant, borrower, flat_product):
    flat_product.is_active = False
    flat_product.save(update_fields=['is_active'])
    with pytest.raises(ValueError, match="not active"):
        LoanService.create_loan(
            product=flat_product, borrower=borrower, tenant=tenant,
            principal_amount=Decimal('5000.00'), term_months=12,
        )


@pytest.mark.django_db
def test_create_loan_rejects_amount_below_min(tenant, borrower, flat_product):
    with pytest.raises(ValueError, match="Principal must be between"):
        LoanService.create_loan(
            product=flat_product, borrower=borrower, tenant=tenant,
            principal_amount=Decimal('500.00'), term_months=12,
        )


@pytest.mark.django_db
def test_create_loan_rejects_amount_above_max(tenant, borrower, flat_product):
    with pytest.raises(ValueError, match="Principal must be between"):
        LoanService.create_loan(
            product=flat_product, borrower=borrower, tenant=tenant,
            principal_amount=Decimal('100000.00'), term_months=12,
        )


@pytest.mark.django_db
def test_create_loan_rejects_term_below_min(tenant, borrower, flat_product):
    with pytest.raises(ValueError, match="Term must be between"):
        LoanService.create_loan(
            product=flat_product, borrower=borrower, tenant=tenant,
            principal_amount=Decimal('5000.00'), term_months=1,
        )


@pytest.mark.django_db
def test_create_loan_rejects_term_above_max(tenant, borrower, flat_product):
    with pytest.raises(ValueError, match="Term must be between"):
        LoanService.create_loan(
            product=flat_product, borrower=borrower, tenant=tenant,
            principal_amount=Decimal('5000.00'), term_months=36,
        )


@pytest.mark.django_db
def test_create_loan_idempotency_returns_existing(tenant, borrower, flat_product):
    loan1 = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=12,
        idempotency_key='key-abc',
    )
    loan2 = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('9000.00'), term_months=6,  # different params
        idempotency_key='key-abc',
    )
    assert loan1.pk == loan2.pk
    assert Loan.objects_unscoped.filter(tenant=tenant).count() == 1


# ---------------------------------------------------------------------------
# LoanService — state transitions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_submit_loan(tenant, borrower, flat_product):
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=12,
    )
    loan = LoanService.submit_loan(loan)
    assert loan.status == LoanStatus.SUBMITTED
    assert loan.submitted_at is not None


@pytest.mark.django_db
def test_submit_already_submitted_raises(tenant, borrower, flat_product):
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    with pytest.raises(InvalidStateTransitionError):
        LoanService.submit_loan(loan)


@pytest.mark.django_db
def test_approve_loan_from_submitted(tenant, borrower, manager, flat_product):
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    loan = LoanService.approve_loan(loan, manager)
    assert loan.status == LoanStatus.APPROVED
    assert loan.approved_by == manager
    assert loan.approved_at is not None


@pytest.mark.django_db
def test_approve_loan_from_under_review(tenant, borrower, manager, flat_product):
    from apps.finance.state_machines.loan_state_machine import loan_state_machine

    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    loan_state_machine.transition(loan, 'status', LoanStatus.UNDER_REVIEW)
    loan = LoanService.approve_loan(loan, manager)
    assert loan.status == LoanStatus.APPROVED


@pytest.mark.django_db
def test_invalid_transition_raises_error(tenant, borrower, flat_product):
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=12,
    )
    with pytest.raises(InvalidStateTransitionError):
        from apps.finance.state_machines.loan_state_machine import loan_state_machine
        loan_state_machine.transition(loan, 'status', LoanStatus.APPROVED)


@pytest.mark.django_db
def test_default_loan(tenant, borrower, manager, flat_product):
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, manager)
    Membership.objects.get_or_create(tenant=tenant, user=borrower, defaults={'status': 'active'})
    loan = LoanService.disburse_loan(loan)
    loan = LoanService.default_loan(loan)
    assert loan.status == LoanStatus.DEFAULTED


# ---------------------------------------------------------------------------
# LoanService — disburse_loan
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_disburse_loan_creates_wallet_and_credits(tenant, borrower, manager, flat_product):
    Membership.objects.get_or_create(tenant=tenant, user=borrower, defaults={'status': 'active'})
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('10000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, manager)
    loan = LoanService.disburse_loan(loan)

    assert loan.status == LoanStatus.ACTIVE
    assert loan.disbursed_at is not None

    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    assert wallet.balance == Decimal('10000.00')


@pytest.mark.django_db
def test_disburse_loan_uses_existing_wallet(tenant, borrower, manager, flat_product):
    from apps.finance.services.wallet_service import WalletService

    Membership.objects.get_or_create(tenant=tenant, user=borrower, defaults={'status': 'active'})
    existing_wallet = WalletService.create_wallet(borrower, tenant)

    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, manager)
    LoanService.disburse_loan(loan)

    # No duplicate wallet created
    assert Wallet.objects_unscoped.filter(tenant=tenant, owner=borrower).count() == 1
    existing_wallet.refresh_from_db()
    assert existing_wallet.balance == Decimal('5000.00')


@pytest.mark.django_db
def test_disburse_loan_creates_transaction_record(tenant, borrower, manager, flat_product):
    from apps.finance.models import Transaction

    Membership.objects.get_or_create(tenant=tenant, user=borrower, defaults={'status': 'active'})
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('8000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, manager)
    LoanService.disburse_loan(loan)

    txn = Transaction.objects_unscoped.get(loan=loan)
    assert txn.transaction_type == 'disbursement'
    assert txn.amount == Decimal('8000.00')
    assert txn.status == 'completed'


@pytest.mark.django_db
def test_disburse_loan_ledger_balance_holds(tenant, borrower, manager, flat_product):
    from apps.finance.services.ledger_service import LedgerService

    Membership.objects.get_or_create(tenant=tenant, user=borrower, defaults={'status': 'active'})
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('6000.00'), term_months=12,
    )
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, manager)
    LoanService.disburse_loan(loan)

    assert LedgerService.validate_balance(tenant) is True


# ---------------------------------------------------------------------------
# LoanService — compute_schedule
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_compute_schedule_flat(tenant, borrower, flat_product):
    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('12000.00'), term_months=12,
    )
    schedule = LoanService.compute_schedule(loan)
    assert schedule['term_months'] == 12
    assert len(schedule['installments']) == 12
    assert schedule['total_interest'] == str(loan.interest_amount)
    # Each installment has equal payment
    payments = {i['payment'] for i in schedule['installments']}
    assert len(payments) == 1


@pytest.mark.django_db
def test_compute_schedule_reducing_balance(tenant, borrower, rb_product):
    loan = LoanService.create_loan(
        product=rb_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('10000.00'), term_months=12,
    )
    schedule = LoanService.compute_schedule(loan)
    assert len(schedule['installments']) == 12
    # Interest portion decreases over time in reducing balance
    interests = [Decimal(i['interest']) for i in schedule['installments']]
    assert interests[0] > interests[-1]


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_full_loan_lifecycle(tenant, borrower, manager, flat_product):
    Membership.objects.get_or_create(tenant=tenant, user=borrower, defaults={'status': 'active'})

    loan = LoanService.create_loan(
        product=flat_product, borrower=borrower, tenant=tenant,
        principal_amount=Decimal('5000.00'), term_months=6,
    )
    assert loan.status == LoanStatus.CREATED

    loan = LoanService.submit_loan(loan)
    assert loan.status == LoanStatus.SUBMITTED

    loan = LoanService.approve_loan(loan, manager)
    assert loan.status == LoanStatus.APPROVED

    loan = LoanService.disburse_loan(loan)
    assert loan.status == LoanStatus.ACTIVE

    wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
    assert wallet.balance == Decimal('5000.00')


# ---------------------------------------------------------------------------
# API — Loans
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_api_create_loan(api_client, setup_rbac, flat_product):
    _auth(api_client, setup_rbac['borrower'])
    payload = {
        'product': str(flat_product.pk),
        'borrower': str(setup_rbac['borrower'].pk),
        'principal_amount': '10000.00',
        'term_months': 12,
    }
    response = api_client.post('/api/v1/finance/loans/', payload, format='json')
    assert response.status_code == 201
    assert response.data['status'] == 'created'
    assert Decimal(response.data['interest_amount']) == Decimal('1200.00')


@pytest.mark.django_db
def test_api_list_loans_tenant_scoped(api_client, setup_rbac, flat_product):
    tenant2 = Tenant.objects.create(name='Other Bank', slug='other-bank')
    LoanProduct.objects_unscoped.create(
        tenant=tenant2, name='Other Product',
        interest_type=InterestType.FLAT, interest_rate=Decimal('10.00'),
        min_term_months=1, max_term_months=12,
        min_amount=Decimal('500.00'), max_amount=Decimal('10000.00'),
    )

    _auth(api_client, setup_rbac['borrower'])
    payload = {
        'product': str(flat_product.pk),
        'borrower': str(setup_rbac['borrower'].pk),
        'principal_amount': '5000.00',
        'term_months': 6,
    }
    api_client.post('/api/v1/finance/loans/', payload, format='json')

    response = api_client.get('/api/v1/finance/loans/')
    assert response.status_code == 200
    assert len(response.data['results']) == 1


@pytest.mark.django_db
def test_api_get_schedule(api_client, setup_rbac, flat_product):
    _auth(api_client, setup_rbac['borrower'])
    create_resp = api_client.post('/api/v1/finance/loans/', {
        'product': str(flat_product.pk),
        'borrower': str(setup_rbac['borrower'].pk),
        'principal_amount': '12000.00',
        'term_months': 12,
    }, format='json')
    loan_id = create_resp.data['id']

    response = api_client.get(f'/api/v1/finance/loans/{loan_id}/schedule/')
    assert response.status_code == 200
    assert response.data['term_months'] == 12
    assert len(response.data['installments']) == 12


@pytest.mark.django_db
def test_api_submit_loan(api_client, setup_rbac, flat_product):
    _auth(api_client, setup_rbac['borrower'])
    create_resp = api_client.post('/api/v1/finance/loans/', {
        'product': str(flat_product.pk),
        'borrower': str(setup_rbac['borrower'].pk),
        'principal_amount': '5000.00',
        'term_months': 12,
    }, format='json')
    loan_id = create_resp.data['id']

    response = api_client.post(f'/api/v1/finance/loans/{loan_id}/submit/')
    assert response.status_code == 200
    assert response.data['status'] == 'submitted'


@pytest.mark.django_db
def test_api_approve_requires_permission(api_client, setup_rbac, flat_product):
    """Regular borrower cannot approve."""
    _auth(api_client, setup_rbac['borrower'])
    create_resp = api_client.post('/api/v1/finance/loans/', {
        'product': str(flat_product.pk),
        'borrower': str(setup_rbac['borrower'].pk),
        'principal_amount': '5000.00',
        'term_months': 12,
    }, format='json')
    loan_id = create_resp.data['id']
    api_client.post(f'/api/v1/finance/loans/{loan_id}/submit/')

    response = api_client.post(f'/api/v1/finance/loans/{loan_id}/approve/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_api_approve_with_permission(api_client, setup_rbac, flat_product):
    borrower = setup_rbac['borrower']
    manager = setup_rbac['manager']

    _auth(api_client, borrower)
    create_resp = api_client.post('/api/v1/finance/loans/', {
        'product': str(flat_product.pk),
        'borrower': str(borrower.pk),
        'principal_amount': '5000.00',
        'term_months': 12,
    }, format='json')
    loan_id = create_resp.data['id']
    api_client.post(f'/api/v1/finance/loans/{loan_id}/submit/')

    _auth(api_client, manager)
    response = api_client.post(f'/api/v1/finance/loans/{loan_id}/approve/')
    assert response.status_code == 200
    assert response.data['status'] == 'approved'
    assert str(response.data['approved_by']) == str(manager.pk)


@pytest.mark.django_db
def test_api_disburse_with_permission(api_client, setup_rbac, flat_product):
    borrower = setup_rbac['borrower']
    manager = setup_rbac['manager']

    _auth(api_client, borrower)
    create_resp = api_client.post('/api/v1/finance/loans/', {
        'product': str(flat_product.pk),
        'borrower': str(borrower.pk),
        'principal_amount': '5000.00',
        'term_months': 12,
    }, format='json')
    loan_id = create_resp.data['id']
    api_client.post(f'/api/v1/finance/loans/{loan_id}/submit/')

    _auth(api_client, manager)
    api_client.post(f'/api/v1/finance/loans/{loan_id}/approve/')
    response = api_client.post(f'/api/v1/finance/loans/{loan_id}/disburse/')

    assert response.status_code == 200
    assert response.data['status'] == 'active'

    wallet = Wallet.objects_unscoped.get(tenant=setup_rbac['tenant'], owner=borrower)
    assert wallet.balance == Decimal('5000.00')
