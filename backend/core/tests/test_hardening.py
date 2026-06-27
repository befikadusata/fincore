import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.saas.models import User


@pytest.mark.django_db
class TestRegisterValidation:
    url = '/api/v1/saas/auth/register/'

    def test_short_password_rejected(self):
        client = APIClient()
        resp = client.post(self.url, {'email': 'a@b.com', 'password': '123'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in resp.data

    def test_invalid_email_rejected(self):
        client = APIClient()
        resp = client.post(self.url, {'email': 'not-an-email', 'password': 'validpass1'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in resp.data

    def test_valid_registration_still_works(self):
        client = APIClient()
        resp = client.post(self.url, {'email': 'valid@example.com', 'password': 'Strongpass1'})
        assert resp.status_code == status.HTTP_201_CREATED

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email='dup@example.com', password='pass123456')
        client = APIClient()
        resp = client.post(self.url, {'email': 'dup@example.com', 'password': 'Anotherpass1'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoanSerializerValidation:
    def _make_client(self):
        user = User.objects.create_user(email='lender@example.com', password='pass12345')
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_zero_principal_rejected(self):
        from apps.finance.api.v1.serializers import LoanSerializer
        s = LoanSerializer(data={'principal_amount': '0', 'term_months': 12, 'product': None})
        s.is_valid()
        assert 'principal_amount' in s.errors

    def test_negative_principal_rejected(self):
        from apps.finance.api.v1.serializers import LoanSerializer
        s = LoanSerializer(data={'principal_amount': '-100', 'term_months': 12, 'product': None})
        s.is_valid()
        assert 'principal_amount' in s.errors

    def test_zero_term_rejected(self):
        from apps.finance.api.v1.serializers import LoanSerializer
        s = LoanSerializer(data={'principal_amount': '1000', 'term_months': 0, 'product': None})
        s.is_valid()
        assert 'term_months' in s.errors

    def test_excessive_term_rejected(self):
        from apps.finance.api.v1.serializers import LoanSerializer
        s = LoanSerializer(data={'principal_amount': '1000', 'term_months': 999, 'product': None})
        s.is_valid()
        assert 'term_months' in s.errors


@pytest.mark.django_db
class TestSchemaEndpoint:
    def test_schema_returns_openapi_json(self):
        user = User.objects.create_user(email='schema@example.com', password='pass12345')
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get('/api/schema/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp['Content-Type'].startswith('application/vnd.oai.openapi')
