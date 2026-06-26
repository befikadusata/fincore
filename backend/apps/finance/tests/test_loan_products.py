import pytest
from decimal import Decimal

from apps.saas.models import Tenant, User, Membership, Role, Permission, RolePermission
from apps.saas.services.rbac import RBACService
from apps.finance.models import LoanProduct
from apps.finance.constants import InterestType
from apps.finance.services.interest import (
    FlatInterestCalculator,
    ReducingBalanceCalculator,
    InterestCalculatorFactory,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Test Lender', slug='test-lender')


@pytest.fixture
def product(tenant):
    return LoanProduct.objects_unscoped.create(
        tenant=tenant,
        name='Standard Loan',
        interest_type=InterestType.FLAT,
        interest_rate=Decimal('18.00'),
        min_term_months=3,
        max_term_months=24,
        min_amount=Decimal('1000.00'),
        max_amount=Decimal('50000.00'),
    )


# ---------------------------------------------------------------------------
# FlatInterestCalculator
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_flat_interest_basic():
    calc = FlatInterestCalculator()
    # 12,000 principal, 12% p.a., 12 months → interest = 12000 × 0.12 × 1 = 1440
    result = calc.calculate(Decimal('12000.00'), Decimal('12.00'), 12)
    assert result.total_interest == Decimal('1440.00')
    assert result.total_repayable == Decimal('13440.00')
    assert result.monthly_payment == Decimal('1120.00')


@pytest.mark.django_db
def test_flat_interest_short_term():
    calc = FlatInterestCalculator()
    # 6,000 principal, 18% p.a., 6 months → interest = 6000 × 0.18 × 0.5 = 540
    result = calc.calculate(Decimal('6000.00'), Decimal('18.00'), 6)
    assert result.total_interest == Decimal('540.00')
    assert result.total_repayable == Decimal('6540.00')


@pytest.mark.django_db
def test_flat_interest_zero_rate():
    calc = FlatInterestCalculator()
    result = calc.calculate(Decimal('10000.00'), Decimal('0.00'), 12)
    assert result.total_interest == Decimal('0.00')
    assert result.total_repayable == Decimal('10000.00')
    assert result.monthly_payment == Decimal('833.33')


@pytest.mark.django_db
def test_flat_interest_rejects_zero_principal():
    calc = FlatInterestCalculator()
    with pytest.raises(ValueError, match="principal"):
        calc.calculate(Decimal('0'), Decimal('12.00'), 12)


@pytest.mark.django_db
def test_flat_interest_rejects_zero_term():
    calc = FlatInterestCalculator()
    with pytest.raises(ValueError, match="term_months"):
        calc.calculate(Decimal('10000.00'), Decimal('12.00'), 0)


@pytest.mark.django_db
def test_flat_interest_rejects_negative_rate():
    calc = FlatInterestCalculator()
    with pytest.raises(ValueError, match="annual_rate"):
        calc.calculate(Decimal('10000.00'), Decimal('-1.00'), 12)


# ---------------------------------------------------------------------------
# ReducingBalanceCalculator
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_reducing_balance_basic():
    calc = ReducingBalanceCalculator()
    # 10,000 at 12% p.a. for 12 months
    # r = 0.01, PMT = 10000 × 0.01 × 1.01^12 / (1.01^12 − 1) ≈ 888.49
    result = calc.calculate(Decimal('10000.00'), Decimal('12.00'), 12)
    assert result.monthly_payment == Decimal('888.49')
    assert result.total_repayable == Decimal('10661.88')
    assert result.total_interest == Decimal('661.88')


@pytest.mark.django_db
def test_reducing_balance_lower_interest_than_flat():
    """For same principal/rate/term, reducing balance always yields less total interest than flat."""
    flat = FlatInterestCalculator()
    reducing = ReducingBalanceCalculator()
    p, r, n = Decimal('20000.00'), Decimal('15.00'), 24

    flat_result = flat.calculate(p, r, n)
    reducing_result = reducing.calculate(p, r, n)

    assert reducing_result.total_interest < flat_result.total_interest


@pytest.mark.django_db
def test_reducing_balance_zero_rate():
    calc = ReducingBalanceCalculator()
    result = calc.calculate(Decimal('12000.00'), Decimal('0.00'), 12)
    assert result.monthly_payment == Decimal('1000.00')
    assert result.total_interest == Decimal('0.00')


@pytest.mark.django_db
def test_reducing_balance_rejects_invalid_inputs():
    calc = ReducingBalanceCalculator()
    with pytest.raises(ValueError):
        calc.calculate(Decimal('0'), Decimal('12.00'), 12)
    with pytest.raises(ValueError):
        calc.calculate(Decimal('1000.00'), Decimal('12.00'), 0)


# ---------------------------------------------------------------------------
# InterestCalculatorFactory
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_factory_returns_flat_calculator(product):
    product.interest_type = InterestType.FLAT
    calc = InterestCalculatorFactory.for_product(product)
    assert isinstance(calc, FlatInterestCalculator)


@pytest.mark.django_db
def test_factory_returns_reducing_balance_calculator(product):
    product.interest_type = InterestType.REDUCING_BALANCE
    calc = InterestCalculatorFactory.for_product(product)
    assert isinstance(calc, ReducingBalanceCalculator)


@pytest.mark.django_db
def test_factory_raises_for_unregistered_type(product):
    product.interest_type = InterestType.COMPOUND
    with pytest.raises(NotImplementedError):
        InterestCalculatorFactory.for_product(product)


@pytest.mark.django_db
def test_factory_get_by_string():
    assert isinstance(InterestCalculatorFactory.get(InterestType.FLAT), FlatInterestCalculator)
    assert isinstance(InterestCalculatorFactory.get(InterestType.REDUCING_BALANCE), ReducingBalanceCalculator)


# ---------------------------------------------------------------------------
# LoanProduct model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_loan_product_create(product):
    assert product.pk is not None
    assert product.is_active is True
    assert product.currency == 'ETB'
    assert product.fees_config == {}


@pytest.mark.django_db
def test_loan_product_tenant_isolation(db):
    t1 = Tenant.objects.create(name='Lender A', slug='lender-a')
    t2 = Tenant.objects.create(name='Lender B', slug='lender-b')

    LoanProduct.objects_unscoped.create(
        tenant=t1, name='Product A',
        interest_type=InterestType.FLAT, interest_rate=Decimal('12.00'),
        min_term_months=1, max_term_months=12,
        min_amount=Decimal('500.00'), max_amount=Decimal('10000.00'),
    )

    assert LoanProduct.objects_unscoped.filter(tenant=t1).count() == 1
    assert LoanProduct.objects_unscoped.filter(tenant=t2).count() == 0


@pytest.mark.django_db
def test_loan_product_fees_config(tenant):
    p = LoanProduct.objects_unscoped.create(
        tenant=tenant,
        name='Fee Product',
        interest_type=InterestType.FLAT,
        interest_rate=Decimal('15.00'),
        min_term_months=3,
        max_term_months=12,
        min_amount=Decimal('1000.00'),
        max_amount=Decimal('20000.00'),
        fees_config={'origination_fee_pct': 2.0, 'insurance_fee_pct': 0.5},
    )
    p.refresh_from_db()
    assert p.fees_config['origination_fee_pct'] == 2.0


# ---------------------------------------------------------------------------
# API — LoanProduct CRUD
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(email='admin@lender.com', password='pw')


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(email='member@lender.com', password='pw')


@pytest.fixture
def setup_tenant_with_admin(tenant, admin_user, regular_user):
    """
    Wires up: admin_user gets 'loan_products:manage' permission via role.
    regular_user is a plain member with no manage permission.
    """
    perm = Permission.objects.create(codename='loan_products:manage', description='')
    role = Role.objects_unscoped.create(tenant=tenant, name='LoanAdmin', slug='loan-admin')
    RolePermission.objects.create(role=role, permission=perm)
    Membership.objects.create(tenant=tenant, user=admin_user, status='active')
    Membership.objects.create(tenant=tenant, user=regular_user, status='active')
    RBACService.assign_role(admin_user, tenant, role)
    return tenant


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


@pytest.mark.django_db
def test_api_list_loan_products(api_client, setup_tenant_with_admin, admin_user, product):
    _auth(api_client, admin_user)
    response = api_client.get('/api/v1/finance/loan-products/')
    assert response.status_code == 200
    assert len(response.data['results']) == 1


@pytest.mark.django_db
def test_api_create_loan_product_with_permission(api_client, setup_tenant_with_admin, admin_user):
    _auth(api_client, admin_user)
    payload = {
        'name': 'Business Loan',
        'interest_type': 'flat',
        'interest_rate': '15.0000',
        'min_term_months': 6,
        'max_term_months': 36,
        'min_amount': '5000.00',
        'max_amount': '200000.00',
    }
    response = api_client.post('/api/v1/finance/loan-products/', payload, format='json')
    assert response.status_code == 201
    assert response.data['name'] == 'Business Loan'


@pytest.mark.django_db
def test_api_create_loan_product_forbidden_without_permission(
    api_client, setup_tenant_with_admin, regular_user
):
    _auth(api_client, regular_user)
    payload = {
        'name': 'Unauthorized Product',
        'interest_type': 'flat',
        'interest_rate': '10.0000',
        'min_term_months': 1,
        'max_term_months': 12,
        'min_amount': '500.00',
        'max_amount': '5000.00',
    }
    response = api_client.post('/api/v1/finance/loan-products/', payload, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_api_create_validates_term_range(api_client, setup_tenant_with_admin, admin_user):
    _auth(api_client, admin_user)
    payload = {
        'name': 'Bad Range',
        'interest_type': 'flat',
        'interest_rate': '12.0000',
        'min_term_months': 12,
        'max_term_months': 6,  # invalid: min > max
        'min_amount': '1000.00',
        'max_amount': '10000.00',
    }
    response = api_client.post('/api/v1/finance/loan-products/', payload, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_api_create_validates_amount_range(api_client, setup_tenant_with_admin, admin_user):
    _auth(api_client, admin_user)
    payload = {
        'name': 'Bad Amount',
        'interest_type': 'flat',
        'interest_rate': '12.0000',
        'min_term_months': 1,
        'max_term_months': 12,
        'min_amount': '50000.00',
        'max_amount': '1000.00',  # invalid: min > max
    }
    response = api_client.post('/api/v1/finance/loan-products/', payload, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_api_update_loan_product(api_client, setup_tenant_with_admin, admin_user, product):
    _auth(api_client, admin_user)
    response = api_client.patch(
        f'/api/v1/finance/loan-products/{product.pk}/',
        {'name': 'Updated Name'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['name'] == 'Updated Name'


@pytest.mark.django_db
def test_api_delete_loan_product(api_client, setup_tenant_with_admin, admin_user, product):
    _auth(api_client, admin_user)
    response = api_client.delete(f'/api/v1/finance/loan-products/{product.pk}/')
    assert response.status_code == 204
    assert not LoanProduct.objects_unscoped.filter(pk=product.pk).exists()
