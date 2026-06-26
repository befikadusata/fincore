import pytest
from rest_framework.test import APIClient
from apps.saas.models import Tenant, User, Membership, Role, Permission, RolePermission
from apps.saas.services.rbac import RBACService


@pytest.fixture
def tenant_and_user(db):
    tenant = Tenant.objects.create(name='Acme', slug='acme')
    user = User.objects.create_user(email='user@test.com', password='pass123')
    Membership.objects.create(user=user, tenant=tenant, status='active')
    return tenant, user


@pytest.mark.django_db
def test_assign_role(tenant_and_user):
    tenant, user = tenant_and_user
    role = Role.objects_unscoped.create(
        name='Admin', slug='admin', tenant=tenant
    )

    RBACService.assign_role(user, tenant, role)

    # Verify via the forward M2M (avoids TenantManager on reverse accessor)
    membership = Membership.objects.get(user=user, tenant=tenant)
    assert role.membership.filter(id=membership.id).exists()


@pytest.mark.django_db
def test_check_permission_true(tenant_and_user):
    tenant, user = tenant_and_user
    role = Role.objects_unscoped.create(
        name='Admin', slug='admin', tenant=tenant
    )
    permission = Permission.objects.create(
        codename='view_reports', description='Can view reports'
    )
    RolePermission.objects.create(role=role, permission=permission)

    RBACService.assign_role(user, tenant, role)

    assert RBACService.check_permission(user, tenant, 'view_reports') is True


@pytest.mark.django_db
def test_check_permission_false(tenant_and_user):
    tenant, user = tenant_and_user
    permission = Permission.objects.create(
        codename='admin_access', description='Admin access'
    )

    assert RBACService.check_permission(user, tenant, 'admin_access') is False


@pytest.mark.django_db
def test_remove_role(tenant_and_user):
    tenant, user = tenant_and_user
    role = Role.objects_unscoped.create(
        name='Admin', slug='admin', tenant=tenant
    )
    permission = Permission.objects.create(
        codename='view_reports', description='Can view reports'
    )
    RolePermission.objects.create(role=role, permission=permission)

    RBACService.assign_role(user, tenant, role)
    assert RBACService.check_permission(user, tenant, 'view_reports') is True

    RBACService.remove_role(user, tenant, role)
    assert RBACService.check_permission(user, tenant, 'view_reports') is False


@pytest.mark.django_db
def test_assign_permissions_requires_permission(tenant_and_user):
    tenant, user = tenant_and_user
    role = Role.objects_unscoped.create(name='Editor', slug='editor', tenant=tenant)
    perm = Permission.objects.create(codename='edit_docs', description='Edit documents')

    client = APIClient()
    client.force_authenticate(user)

    # Plain member with no roles:assign_permissions — must be rejected
    response = client.post(
        f'/api/v1/saas/roles/{role.id}/assign_permissions/',
        {'permission_ids': [str(perm.id)]},
        format='json',
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_assign_permissions_allowed_with_permission(tenant_and_user):
    tenant, user = tenant_and_user
    role = Role.objects_unscoped.create(name='Editor', slug='editor', tenant=tenant)
    perm1 = Permission.objects.create(codename='edit_docs', description='Edit documents')
    perm2 = Permission.objects.create(codename='publish', description='Publish content')

    manage_perm = Permission.objects.create(
        codename='roles:assign_permissions', description='Assign permissions to roles'
    )
    admin_role = Role.objects_unscoped.create(name='Admin', slug='admin', tenant=tenant)
    RolePermission.objects.create(role=admin_role, permission=manage_perm)
    RBACService.assign_role(user, tenant, admin_role)

    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        f'/api/v1/saas/roles/{role.id}/assign_permissions/',
        {'permission_ids': [str(perm1.id), str(perm2.id)]},
        format='json',
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 200
    assert RolePermission.objects.filter(role=role).count() == 2


@pytest.mark.django_db
def test_assign_members_requires_permission(tenant_and_user):
    tenant, user = tenant_and_user
    target = User.objects.create_user(email='target@test.com', password='pass123')
    Membership.objects.create(user=target, tenant=tenant, status='active')
    role = Role.objects_unscoped.create(name='Editor', slug='editor', tenant=tenant)

    client = APIClient()
    client.force_authenticate(user)

    # Plain member with no roles:assign_members — must be rejected
    response = client.post(
        f'/api/v1/saas/roles/{role.id}/assign_members/',
        {'user_ids': [str(target.id)]},
        format='json',
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_assign_members_allowed_with_permission(tenant_and_user):
    tenant, user = tenant_and_user
    target = User.objects.create_user(email='target@test.com', password='pass123')
    Membership.objects.create(user=target, tenant=tenant, status='active')
    role = Role.objects_unscoped.create(name='Editor', slug='editor', tenant=tenant)

    manage_perm = Permission.objects.create(
        codename='roles:assign_members', description='Assign members to roles'
    )
    admin_role = Role.objects_unscoped.create(name='Admin', slug='admin', tenant=tenant)
    RolePermission.objects.create(role=admin_role, permission=manage_perm)
    RBACService.assign_role(user, tenant, admin_role)

    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        f'/api/v1/saas/roles/{role.id}/assign_members/',
        {'user_ids': [str(target.id)]},
        format='json',
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 200
    membership = Membership.objects.get(user=target, tenant=tenant)
    assert role.membership.filter(id=membership.id).exists()
