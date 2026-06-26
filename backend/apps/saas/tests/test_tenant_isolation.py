import pytest
from rest_framework.test import APIClient
from apps.saas.models import Tenant, User, Membership, Role
from core.middleware.tenant import set_current_tenant, clear_current_tenant


@pytest.fixture
def tenants(db):
    t1 = Tenant.objects.create(name='Tenant 1', slug='tenant-1')
    t2 = Tenant.objects.create(name='Tenant 2', slug='tenant-2')
    return t1, t2


@pytest.fixture
def roles(db, tenants):
    t1, t2 = tenants
    r1 = Role.objects_unscoped.create(name='Admin', slug='admin', tenant=t1)
    r2 = Role.objects_unscoped.create(name='Member', slug='member', tenant=t2)
    return r1, r2


@pytest.fixture
def user_and_tenant(db):
    tenant = Tenant.objects.create(name='Acme', slug='acme')
    user = User.objects.create_user(email='user@test.com', password='pass123')
    Membership.objects.create(user=user, tenant=tenant, status='active')
    return user, tenant


@pytest.mark.django_db
def test_tenant_isolation(roles, tenants):
    r1, r2 = roles
    t1, t2 = tenants

    set_current_tenant(t1)
    results = Role.objects.all()
    assert results.count() == 1
    assert results.first().tenant == t1

    set_current_tenant(t2)
    results = Role.objects.all()
    assert results.count() == 1
    assert results.first().tenant == t2

    assert Role.objects_unscoped.all().count() == 2

    clear_current_tenant()

    # No tenant context → TenantManager returns empty; use objects_unscoped for cross-tenant count
    assert Role.objects_unscoped.all().count() == 2


@pytest.mark.django_db
def test_tenant_scoped_endpoint_rejected_without_context(user_and_tenant):
    user, tenant = user_and_tenant
    client = APIClient()
    client.force_authenticate(user)

    # No X-Tenant-ID header, no JWT — tenant context is empty
    # IsTenantMember on the viewset rejects all actions
    response = client.get('/api/v1/saas/roles/')
    assert response.status_code == 403

    response = client.post('/api/v1/saas/roles/', {
        'name': 'Hacker', 'slug': 'hacker',
    })
    assert response.status_code == 403


@pytest.mark.django_db
def test_invalid_tenant_id_rejected(user_and_tenant):
    user, tenant = user_and_tenant
    client = APIClient()
    client.force_authenticate(user)

    fake_id = '00000000-0000-0000-0000-000000000000'
    response = client.get(
        '/api/v1/saas/members/',
        HTTP_X_TENANT_ID=fake_id,
    )
    # No membership exists for this fake tenant — IsTenantMember returns False
    assert response.status_code == 403


@pytest.mark.django_db
def test_unscoped_bypasses_tenant_manager(user_and_tenant):
    user, tenant = user_and_tenant

    # Create roles across two tenants
    other = Tenant.objects.create(name='Other', slug='other')
    our_role = Role.objects_unscoped.create(
        name='Admin', slug='admin', tenant=tenant,
    )
    other_role = Role.objects_unscoped.create(
        name='Member', slug='member', tenant=other,
    )

    set_current_tenant(tenant)

    # TenantManager scopes to current tenant
    assert list(Role.objects.all()) == [our_role]

    # unscoped bypass returns all regardless of tenant context
    assert set(Role.objects_unscoped.all()) == {our_role, other_role}

    clear_current_tenant()


@pytest.mark.django_db
def test_cross_tenant_data_invisible(tenants):
    t1, t2 = tenants
    r1 = Role.objects_unscoped.create(name='T1 Role', slug='t1-role', tenant=t1)
    r2 = Role.objects_unscoped.create(name='T2 Role', slug='t2-role', tenant=t2)

    set_current_tenant(t1)
    roles_in_t1 = list(Role.objects.all())
    assert roles_in_t1 == [r1]
    assert r2 not in roles_in_t1

    set_current_tenant(t2)
    roles_in_t2 = list(Role.objects.all())
    assert roles_in_t2 == [r2]
    assert r1 not in roles_in_t2

    clear_current_tenant()
