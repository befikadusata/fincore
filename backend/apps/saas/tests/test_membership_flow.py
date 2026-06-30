import pytest
from rest_framework.test import APIClient
from apps.saas.models import Tenant, User, Membership
from core.middleware.tenant import set_current_tenant, clear_current_tenant


@pytest.fixture
def tenant_and_owner(db):
    owner = User.objects.create_user(email='owner@test.com', password='pass123')
    tenant = Tenant.objects.create(name='Acme', slug='acme')
    Membership.objects.create(user=owner, tenant=tenant, status='active')
    return tenant, owner


@pytest.mark.django_db
def test_invite_member(tenant_and_owner):
    tenant, owner = tenant_and_owner
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        '/api/v1/members/invite/',
        {'email': 'new@test.com'},
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 201
    assert Membership.objects.filter(
        tenant=tenant, user__email='new@test.com', status='invited'
    ).exists()


@pytest.mark.django_db
def test_remove_member(tenant_and_owner):
    tenant, owner = tenant_and_owner
    member = User.objects.create_user(email='member@test.com', password='pass123')
    membership = Membership.objects.create(
        user=member, tenant=tenant, status='active'
    )

    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f'/api/v1/members/{membership.id}/remove/',
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 204
    membership.refresh_from_db()
    assert membership.status == 'removed'


@pytest.mark.django_db
def test_me_endpoint(tenant_and_owner):
    tenant, owner = tenant_and_owner
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get('/api/v1/auth/me/')
    assert response.status_code == 200
    assert response.data['user']['email'] == 'owner@test.com'
    assert len(response.data['tenants']) == 1
    assert response.data['tenants'][0]['slug'] == 'acme'
