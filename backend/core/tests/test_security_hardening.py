import pytest
from cryptography.fernet import Fernet
from rest_framework import status
from rest_framework.test import APIClient

from apps.saas.models import User

TOKEN_URL = '/api/v1/auth/token/'
REGISTER_URL = '/api/v1/auth/register/'
LOGOUT_URL = '/api/v1/auth/logout/'


def _obtain_tokens(email, password):
    client = APIClient()
    resp = client.post(TOKEN_URL, {'email': email, 'password': password})
    return resp.data


@pytest.mark.django_db
class TestLogout:
    def _user_with_tokens(self):
        User.objects.create_user(email='logout@example.com', password='Logoutpass1')
        return _obtain_tokens('logout@example.com', 'Logoutpass1')

    def test_valid_logout_returns_204(self):
        tokens = self._user_with_tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        resp = client.post(LOGOUT_URL, {'refresh': tokens['refresh']})
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_without_refresh_token_returns_400(self):
        tokens = self._user_with_tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        resp = client.post(LOGOUT_URL, {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_with_garbage_token_returns_400(self):
        tokens = self._user_with_tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        resp = client.post(LOGOUT_URL, {'refresh': 'not-a-valid-token'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_double_logout_returns_400(self):
        tokens = self._user_with_tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        client.post(LOGOUT_URL, {'refresh': tokens['refresh']})
        resp = client.post(LOGOUT_URL, {'refresh': tokens['refresh']})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_requires_authentication(self):
        client = APIClient()
        resp = client.post(LOGOUT_URL, {'refresh': 'sometoken'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPasswordComplexity:
    def test_no_uppercase_rejected(self):
        client = APIClient()
        resp = client.post(REGISTER_URL, {'email': 'a@b.com', 'password': 'nouppercase1'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in resp.data

    def test_no_digit_rejected(self):
        client = APIClient()
        resp = client.post(REGISTER_URL, {'email': 'a@b.com', 'password': 'NoDigitPassword'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in resp.data

    def test_too_short_rejected(self):
        client = APIClient()
        resp = client.post(REGISTER_URL, {'email': 'a@b.com', 'password': 'Sh0rt'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in resp.data

    def test_compliant_password_accepted(self):
        client = APIClient()
        resp = client.post(REGISTER_URL, {'email': 'newuser@example.com', 'password': 'Compliant1pass'})
        assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestSecurityHeaders:
    def test_csp_header_present(self):
        client = APIClient()
        resp = client.get('/api/schema/')
        assert 'Content-Security-Policy' in resp

    def test_x_content_type_options_nosniff(self):
        client = APIClient()
        resp = client.get('/api/schema/')
        assert resp['X-Content-Type-Options'] == 'nosniff'

    def test_referrer_policy_present(self):
        client = APIClient()
        resp = client.get('/api/schema/')
        assert 'Referrer-Policy' in resp

    def test_csp_blocks_framing(self):
        client = APIClient()
        resp = client.get('/api/schema/')
        csp = resp['Content-Security-Policy']
        assert "frame-ancestors 'none'" in csp


@pytest.mark.django_db
class TestFieldEncryption:
    def test_encrypted_field_round_trip(self, settings):
        settings.ENCRYPTION_KEY = Fernet.generate_key().decode()
        user = User.objects.create_user(
            email='enc@example.com',
            password='Enctest1pass',
            first_name='Alice',
            last_name='Smith',
        )
        fetched = User.objects.get(pk=user.pk)
        assert fetched.first_name == 'Alice'
        assert fetched.last_name == 'Smith'

    def test_encrypted_field_stores_ciphertext_not_plaintext(self, settings):
        from django.db import connection
        settings.ENCRYPTION_KEY = Fernet.generate_key().decode()
        user = User.objects.create_user(
            email='enc2@example.com',
            password='Enctest1pass',
            first_name='Bob',
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT first_name FROM saas_user WHERE id = %s", [user.pk.hex])
            raw = cursor.fetchone()[0]
        assert raw != 'Bob'  # stored as Fernet ciphertext, not plaintext

    def test_no_encryption_key_stores_plaintext(self, settings):
        settings.ENCRYPTION_KEY = ''
        user = User.objects.create_user(
            email='plain@example.com',
            password='Plaintest1pass',
            first_name='Charlie',
        )
        raw = User.objects.filter(pk=user.pk).values('first_name').first()['first_name']
        assert raw == 'Charlie'
