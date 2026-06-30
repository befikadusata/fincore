import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.saas.models import Tenant, User, Membership
from apps.saas.services.tenant import TenantService


@pytest.mark.django_db
def test_create_tenant_flow():
    user = User.objects.create_user(email='owner@test.com', password='pass123')
    client = APIClient()
    client.force_authenticate(user)

    response = client.post('/api/v1/tenants/', {
        'name': 'Acme Corp',
        'slug': 'acme',
    })
    assert response.status_code == 201
    assert response.data['name'] == 'Acme Corp'

    tenant = Tenant.objects.get(slug='acme')
    assert Membership.objects.filter(
        user=user, tenant=tenant, status='active'
    ).exists()


@pytest.mark.django_db
def test_list_user_tenants():
    user = User.objects.create_user(email='user@test.com', password='pass123')
    t1 = Tenant.objects.create(name='T1', slug='t1')
    t2 = Tenant.objects.create(name='T2', slug='t2')
    Membership.objects.create(user=user, tenant=t1, status='active')
    Membership.objects.create(user=user, tenant=t2, status='active')

    client = APIClient()
    client.force_authenticate(user)
    response = client.get('/api/v1/tenants/')
    assert response.status_code == 200
    assert len(response.data['results']) == 2


@pytest.mark.django_db
def test_switch_tenant():
    user = User.objects.create_user(email='user@test.com', password='pass123')
    t1 = Tenant.objects.create(name='T1', slug='t1')
    t2 = Tenant.objects.create(name='T2', slug='t2')
    Membership.objects.create(user=user, tenant=t1, status='active')
    Membership.objects.create(user=user, tenant=t2, status='active')

    client = APIClient()
    client.force_authenticate(user)
    response = client.post('/api/v1/tenants/switch/', {'tenant_id': str(t2.id)})
    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data


@pytest.mark.django_db
def test_switch_tenant_not_member():
    user = User.objects.create_user(email='user@test.com', password='pass123')
    other = Tenant.objects.create(name='Other', slug='other')

    client = APIClient()
    client.force_authenticate(user)
    response = client.post('/api/v1/tenants/switch/', {'tenant_id': str(other.id)})
    assert response.status_code == 403
