import uuid
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.constants import AuditAction, ActorType
from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditService
from apps.saas.models import Membership, Permission, Role, RolePermission, Tenant, User
from apps.saas.services.rbac import RBACService
from core.decorators.audit import auditable
from core.middleware.audit import clear_audit_context, get_audit_context, set_audit_context


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Audit Bank', slug='audit-bank')


@pytest.fixture
def api_client():
    return APIClient()


def _auth(client, user, tenant):
    refresh = RefreshToken.for_user(user)
    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}',
        HTTP_X_TENANT_ID=str(tenant.id),
    )


@pytest.fixture
def audit_reader(db, tenant):
    user = User.objects.create_user(email='auditor@bank.com', password='pw')
    perm = Permission.objects.create(codename='audit:read', description='')
    role = Role.objects_unscoped.create(tenant=tenant, name='Auditor', slug='auditor')
    RolePermission.objects.create(role=role, permission=perm)
    Membership.objects.create(tenant=tenant, user=user, status='active')
    RBACService.assign_role(user, tenant, role)
    return user


# ---------------------------------------------------------------------------
# AuditLog model — immutability
# ---------------------------------------------------------------------------

class TestAuditLogImmutability:
    def test_create_succeeds(self, db, tenant):
        log = AuditLog(
            tenant=tenant,
            action=AuditAction.CREATE,
            entity_type='Loan',
            entity_id='abc',
        )
        log.save()
        assert AuditLog.objects.filter(id=log.id).exists()

    def test_update_raises(self, db, tenant):
        log = AuditLog.objects.create(
            tenant=tenant,
            action=AuditAction.CREATE,
            entity_type='Loan',
            entity_id='abc',
        )
        log.action = AuditAction.UPDATE
        with pytest.raises(ValueError, match='immutable'):
            log.save()

    def test_delete_raises(self, db, tenant):
        log = AuditLog.objects.create(
            tenant=tenant,
            action=AuditAction.CREATE,
            entity_type='Loan',
            entity_id='abc',
        )
        with pytest.raises(ValueError, match='immutable'):
            log.delete()

    def test_queryset_delete_raises(self, db, tenant):
        AuditLog.objects.create(
            tenant=tenant,
            action=AuditAction.CREATE,
            entity_type='Loan',
            entity_id='qs-del',
        )
        with pytest.raises(ValueError, match='immutable'):
            AuditLog.objects.filter(entity_id='qs-del').first().delete()

    def test_ordering_newest_first(self, db, tenant):
        for i in range(3):
            AuditLog.objects.create(
                tenant=tenant,
                action=AuditAction.CREATE,
                entity_type='Wallet',
                entity_id=str(i),
            )
        ids = list(AuditLog.objects.filter(entity_type='Wallet').values_list('entity_id', flat=True))
        assert ids == ['2', '1', '0']


# ---------------------------------------------------------------------------
# AuditService
# ---------------------------------------------------------------------------

class TestAuditServiceLog:
    def test_log_creates_entry(self, db, tenant):
        AuditService.log(
            action=AuditAction.CREATE,
            entity_type='Loan',
            entity_id='loan-1',
            tenant=tenant,
        )
        log = AuditLog.objects.get(entity_type='Loan', entity_id='loan-1')
        assert log.action == AuditAction.CREATE
        assert log.tenant == tenant

    def test_log_stores_changes(self, db, tenant):
        changes = {'status': {'old': 'CREATED', 'new': 'SUBMITTED'}}
        AuditService.log(
            action=AuditAction.STATUS_CHANGE,
            entity_type='Loan',
            entity_id='loan-2',
            changes=changes,
            tenant=tenant,
        )
        log = AuditLog.objects.get(entity_id='loan-2')
        assert log.changes == changes

    def test_log_picks_up_middleware_context(self, db, tenant):
        set_audit_context({
            'ip_address': '192.168.1.1',
            'user_agent': 'TestAgent/1.0',
            'user_id': None,
        })
        try:
            AuditService.log(
                action=AuditAction.LOGIN,
                entity_type='User',
                entity_id='u-1',
                tenant=tenant,
            )
        finally:
            clear_audit_context()

        log = AuditLog.objects.get(entity_id='u-1')
        assert log.ip_address == '192.168.1.1'
        assert log.user_agent == 'TestAgent/1.0'

    def test_log_explicit_args_override_context(self, db, tenant):
        set_audit_context({'ip_address': '10.0.0.1', 'user_agent': 'ctx', 'user_id': None})
        try:
            AuditService.log(
                action=AuditAction.UPDATE,
                entity_type='Wallet',
                entity_id='w-1',
                ip_address='1.2.3.4',
                user_agent='explicit',
                tenant=tenant,
            )
        finally:
            clear_audit_context()

        log = AuditLog.objects.get(entity_id='w-1')
        assert log.ip_address == '1.2.3.4'
        assert log.user_agent == 'explicit'

    def test_log_actor_type_system(self, db, tenant):
        AuditService.log(
            action=AuditAction.UPDATE,
            entity_type='Loan',
            entity_id='sys-loan',
            actor_type=ActorType.SYSTEM,
            tenant=tenant,
        )
        log = AuditLog.objects.get(entity_id='sys-loan')
        assert log.actor_type == ActorType.SYSTEM

    def test_log_null_entity_id(self, db, tenant):
        AuditService.log(
            action=AuditAction.LOGIN,
            entity_type='User',
            tenant=tenant,
        )
        log = AuditLog.objects.filter(entity_type='User', action=AuditAction.LOGIN).first()
        assert log is not None
        assert log.entity_id == ''

    def test_log_does_not_raise_on_db_error(self, db, tenant):
        with patch('apps.audit.models.AuditLog.save', side_effect=Exception('db error')):
            AuditService.log(
                action=AuditAction.CREATE,
                entity_type='Loan',
                entity_id='err-loan',
                tenant=tenant,
            )


class TestAuditServiceGetEntityHistory:
    def test_returns_chronological_history(self, db, tenant):
        for action in [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.STATUS_CHANGE]:
            AuditLog.objects.create(
                tenant=tenant,
                action=action,
                entity_type='Loan',
                entity_id='loan-hist',
            )
        history = list(AuditService.get_entity_history('Loan', 'loan-hist', tenant=tenant))
        assert len(history) == 3
        actions = [h.action for h in history]
        assert actions == [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.STATUS_CHANGE]

    def test_filters_by_tenant(self, db, tenant):
        other = Tenant.objects.create(name='Other', slug='other')
        AuditLog.objects.create(tenant=tenant, action=AuditAction.CREATE, entity_type='Loan', entity_id='shared')
        AuditLog.objects.create(tenant=other, action=AuditAction.UPDATE, entity_type='Loan', entity_id='shared')

        history = list(AuditService.get_entity_history('Loan', 'shared', tenant=tenant))
        assert len(history) == 1
        assert history[0].tenant == tenant

    def test_returns_empty_for_unknown_entity(self, db, tenant):
        history = list(AuditService.get_entity_history('Loan', 'nonexistent', tenant=tenant))
        assert history == []


# ---------------------------------------------------------------------------
# @auditable decorator
# ---------------------------------------------------------------------------

class TestAuditableDecorator:
    def test_decorator_calls_audit_service(self, db, tenant):
        with patch('apps.audit.services.audit_service.AuditService.log') as mock_log:
            @auditable('loan')
            def create_loan(data):
                return MagicMock(id=uuid.uuid4())

            create_loan({'amount': 1000})
            mock_log.assert_called_once()

    def test_decorator_passes_entity_type(self, db):
        with patch('apps.audit.services.audit_service.AuditService.log') as mock_log:
            @auditable('wallet')
            def do_something():
                return None

            do_something()
            call_kwargs = mock_log.call_args
            assert call_kwargs.kwargs['entity_type'] == 'wallet' or call_kwargs.args[1] == 'wallet'

    def test_decorator_explicit_action(self, db):
        with patch('apps.audit.services.audit_service.AuditService.log') as mock_log:
            @auditable('loan', action=AuditAction.STATUS_CHANGE)
            def approve(data):
                return None

            approve({})
            call_kwargs = mock_log.call_args
            logged_action = call_kwargs.kwargs.get('action') or call_kwargs.args[0]
            assert logged_action == AuditAction.STATUS_CHANGE

    def test_decorator_skips_class_arg(self, db):
        """When first arg is a class (classmethod pattern), decorator must not crash."""
        with patch('apps.audit.services.audit_service.AuditService.log') as mock_log:
            @auditable('loan')
            def method(cls):
                return None

            class MyService:
                pass

            method(MyService)
            mock_log.assert_called_once()

    def test_decorator_returns_original_result(self, db):
        expected = {'id': 'abc'}
        with patch('apps.audit.services.audit_service.AuditService.log'):
            @auditable('loan')
            def do():
                return expected

            result = do()
            assert result is expected


# ---------------------------------------------------------------------------
# AuditMiddleware context
# ---------------------------------------------------------------------------

class TestAuditMiddleware:
    def test_context_cleared_after_request(self):
        from django.test import RequestFactory
        from core.middleware.audit import AuditMiddleware

        factory = RequestFactory()
        request = factory.get('/')
        request.user = MagicMock(is_authenticated=False)

        middleware = AuditMiddleware(get_response=lambda r: MagicMock(status_code=200))
        middleware.process_request(request)
        ctx = get_audit_context()
        assert 'ip_address' in ctx

        response = MagicMock(status_code=200)
        middleware.process_response(request, response)
        ctx_after = get_audit_context()
        assert ctx_after.get('ip_address') is None

    def test_context_captures_ip(self):
        from django.test import RequestFactory
        from core.middleware.audit import AuditMiddleware

        factory = RequestFactory(REMOTE_ADDR='203.0.113.1')
        request = factory.get('/')
        request.user = MagicMock(is_authenticated=False)

        middleware = AuditMiddleware(get_response=lambda r: MagicMock())
        middleware.process_request(request)
        assert get_audit_context()['ip_address'] == '203.0.113.1'
        clear_audit_context()

    def test_context_prefers_x_forwarded_for(self):
        from django.test import RequestFactory
        from core.middleware.audit import AuditMiddleware

        factory = RequestFactory(
            REMOTE_ADDR='10.0.0.1',
            HTTP_X_FORWARDED_FOR='203.0.113.5, 10.0.0.1',
        )
        request = factory.get('/')
        request.user = MagicMock(is_authenticated=False)

        middleware = AuditMiddleware(get_response=lambda r: MagicMock())
        middleware.process_request(request)
        assert get_audit_context()['ip_address'] == '203.0.113.5'
        clear_audit_context()


# ---------------------------------------------------------------------------
# API — list & entity history
# ---------------------------------------------------------------------------

class TestAuditLogAPI:
    def _seed(self, tenant, count=3):
        logs = []
        for i in range(count):
            logs.append(AuditLog.objects.create(
                tenant=tenant,
                action=AuditAction.CREATE if i % 2 == 0 else AuditAction.UPDATE,
                entity_type='Loan',
                entity_id=f'loan-{i}',
            ))
        return logs

    def test_list_requires_auth(self, db, api_client):
        resp = api_client.get('/api/v1/audit/logs/')
        assert resp.status_code == 401

    def test_list_requires_permission(self, db, tenant, api_client):
        user = User.objects.create_user(email='noperm@bank.com', password='pw')
        Membership.objects.create(tenant=tenant, user=user, status='active')
        _auth(api_client, user, tenant)
        resp = api_client.get('/api/v1/audit/logs/')
        assert resp.status_code == 403

    def test_list_returns_tenant_logs(self, db, tenant, api_client, audit_reader):
        self._seed(tenant)
        other = Tenant.objects.create(name='Other', slug='other2')
        AuditLog.objects.create(tenant=other, action=AuditAction.CREATE, entity_type='Loan', entity_id='x')

        _auth(api_client, audit_reader, tenant)
        resp = api_client.get('/api/v1/audit/logs/')
        assert resp.status_code == 200
        assert len(resp.data['results']) == 3

    def test_list_filter_by_action(self, db, tenant, api_client, audit_reader):
        self._seed(tenant)
        _auth(api_client, audit_reader, tenant)
        resp = api_client.get('/api/v1/audit/logs/', {'action': AuditAction.CREATE})
        assert resp.status_code == 200
        for item in resp.data['results']:
            assert item['action'] == AuditAction.CREATE

    def test_list_filter_by_entity_type(self, db, tenant, api_client, audit_reader):
        self._seed(tenant)
        AuditLog.objects.create(tenant=tenant, action=AuditAction.UPDATE, entity_type='Wallet', entity_id='w-1')
        _auth(api_client, audit_reader, tenant)
        resp = api_client.get('/api/v1/audit/logs/', {'entity_type': 'Wallet'})
        assert resp.status_code == 200
        assert len(resp.data['results']) == 1
        assert resp.data['results'][0]['entity_type'] == 'Wallet'

    def test_list_filter_by_entity_id(self, db, tenant, api_client, audit_reader):
        self._seed(tenant)
        _auth(api_client, audit_reader, tenant)
        resp = api_client.get('/api/v1/audit/logs/', {'entity_id': 'loan-0'})
        assert resp.status_code == 200
        assert len(resp.data['results']) == 1

    def test_list_filter_by_actor_id(self, db, tenant, api_client, audit_reader):
        actor = uuid.uuid4()
        AuditLog.objects.create(tenant=tenant, action=AuditAction.CREATE, entity_type='Loan', entity_id='a', actor_id=actor)
        AuditLog.objects.create(tenant=tenant, action=AuditAction.CREATE, entity_type='Loan', entity_id='b')

        _auth(api_client, audit_reader, tenant)
        resp = api_client.get('/api/v1/audit/logs/', {'actor_id': str(actor)})
        assert resp.status_code == 200
        assert len(resp.data['results']) == 1

    def test_retrieve_single_log(self, db, tenant, api_client, audit_reader):
        log = AuditLog.objects.create(
            tenant=tenant, action=AuditAction.CREATE, entity_type='Loan', entity_id='detail-1'
        )
        _auth(api_client, audit_reader, tenant)
        resp = api_client.get(f'/api/v1/audit/logs/{log.id}/')
        assert resp.status_code == 200
        assert resp.data['entity_id'] == 'detail-1'


class TestEntityHistoryAPI:
    def test_entity_history_returns_ordered_entries(self, db, tenant, api_client, audit_reader):
        for action in [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.STATUS_CHANGE]:
            AuditLog.objects.create(
                tenant=tenant, action=action, entity_type='Loan', entity_id='hist-loan'
            )
        _auth(api_client, audit_reader, tenant)
        resp = api_client.get('/api/v1/audit/logs/entity-history/', {
            'entity_type': 'Loan',
            'entity_id': 'hist-loan',
        })
        assert resp.status_code == 200
        assert len(resp.data) == 3
        assert resp.data[0]['action'] == AuditAction.CREATE
        assert resp.data[-1]['action'] == AuditAction.STATUS_CHANGE

    def test_entity_history_missing_params_returns_400(self, db, tenant, api_client, audit_reader):
        _auth(api_client, audit_reader, tenant)
        resp = api_client.get('/api/v1/audit/logs/entity-history/', {'entity_type': 'Loan'})
        assert resp.status_code == 400

    def test_entity_history_empty_for_unknown(self, db, tenant, api_client, audit_reader):
        _auth(api_client, audit_reader, tenant)
        resp = api_client.get('/api/v1/audit/logs/entity-history/', {
            'entity_type': 'Loan',
            'entity_id': 'nonexistent',
        })
        assert resp.status_code == 200
        assert resp.data == []

    def test_entity_history_scoped_to_tenant(self, db, tenant, api_client, audit_reader):
        other = Tenant.objects.create(name='Other3', slug='other3')
        AuditLog.objects.create(tenant=tenant, action=AuditAction.CREATE, entity_type='Loan', entity_id='cross')
        AuditLog.objects.create(tenant=other, action=AuditAction.UPDATE, entity_type='Loan', entity_id='cross')

        _auth(api_client, audit_reader, tenant)
        resp = api_client.get('/api/v1/audit/logs/entity-history/', {
            'entity_type': 'Loan',
            'entity_id': 'cross',
        })
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['action'] == AuditAction.CREATE
