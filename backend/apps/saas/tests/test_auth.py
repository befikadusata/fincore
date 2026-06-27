import pytest
from rest_framework.test import APIClient
from apps.saas.models import User

@pytest.mark.django_db
def test_user_registration():
    client = APIClient()
    url = '/api/v1/saas/auth/register/'
    data = {'email': 'test@example.com', 'password': 'Testpassword123'}

    response = client.post(url, data)
    assert response.status_code == 201
    assert User.objects.filter(email='test@example.com').exists()

@pytest.mark.django_db
def test_user_login():
    client = APIClient()
    User.objects.create_user(email='test@example.com', password='Testpassword123')

    url = '/api/v1/auth/token/'
    data = {'email': 'test@example.com', 'password': 'Testpassword123'}

    response = client.post(url, data)
    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data
