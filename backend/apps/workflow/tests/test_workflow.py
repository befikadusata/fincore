import pytest
from unittest.mock import patch

from apps.saas.models import Membership, Permission, Role, RolePermission, Tenant, User
from apps.saas.services.rbac import RBACService
from apps.workflow.constants import StepAction, StepStatus, WorkflowStatus
from apps.workflow.models import WorkflowDefinition, WorkflowInstance, WorkflowStep
from apps.workflow.services.workflow_engine import WorkflowEngine
from apps.workflow.services.workflow_service import WorkflowService, _validate_config


# ---------------------------------------------------------------------------
# Shared config helpers
# ---------------------------------------------------------------------------

def single_step_config(assignee_type=None, assignee_value=None, conditions=None, auto_execute=False):
    step = {
        'order': 1,
        'name': 'Review',
        'type': 'approval',
        'conditions': conditions or [],
        'auto_execute': auto_execute,
    }
    if assignee_type:
        step['assignee_type'] = assignee_type
        step['assignee_value'] = assignee_value
    return {'steps': [step]}


def two_step_config():
    return {
        'steps': [
            {'order': 1, 'name': 'First', 'type': 'approval', 'conditions': [], 'auto_execute': False},
            {'order': 2, 'name': 'Second', 'type': 'approval', 'conditions': [], 'auto_execute': False},
        ]
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Workflow Bank', slug='workflow-bank')


@pytest.fixture
def user(db):
    return User.objects.create_user(email='officer@bank.com', password='pw')


@pytest.fixture
def actor(db):
    return User.objects.create_user(email='actor@bank.com', password='pw')


@pytest.fixture
def role(db, tenant):
    return Role.objects_unscoped.create(tenant=tenant, name='Loan Officer', slug='loan-officer')


@pytest.fixture
def setup_membership(tenant, user, role):
    Membership.objects.create(tenant=tenant, user=user, status='active')
    RBACService.assign_role(user, tenant, role)
    return user


@pytest.fixture
def definition(db, tenant):
    return WorkflowService.create_definition(
        name='Loan Approval',
        trigger_event='loan.submitted',
        config=single_step_config(assignee_type='role', assignee_value='loan-officer'),
        tenant=tenant,
    )


@pytest.fixture
def definition_two_steps(db, tenant):
    return WorkflowService.create_definition(
        name='Two Step',
        trigger_event='loan.submitted',
        config=two_step_config(),
        tenant=tenant,
    )


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestValidateConfig:
    def test_rejects_non_dict(self):
        with pytest.raises(ValueError, match='JSON object'):
            _validate_config([])

    def test_rejects_missing_steps(self):
        with pytest.raises(ValueError, match='steps'):
            _validate_config({})

    def test_rejects_empty_steps(self):
        with pytest.raises(ValueError, match='steps'):
            _validate_config({'steps': []})

    def test_rejects_duplicate_order(self):
        with pytest.raises(ValueError, match='Duplicate'):
            _validate_config({'steps': [
                {'order': 1, 'name': 'A', 'type': 'approval', 'conditions': []},
                {'order': 1, 'name': 'B', 'type': 'approval', 'conditions': []},
            ]})

    def test_rejects_invalid_type(self):
        with pytest.raises(ValueError, match='invalid type'):
            _validate_config({'steps': [
                {'order': 1, 'name': 'X', 'type': 'unknown'}
            ]})

    def test_rejects_invalid_operator(self):
        with pytest.raises(ValueError, match='operator'):
            _validate_config({'steps': [
                {'order': 1, 'name': 'X', 'type': 'approval', 'conditions': [
                    {'field': 'amount', 'operator': 'between', 'value': 0}
                ]}
            ]})

    def test_valid_config_passes(self):
        _validate_config(single_step_config())  # no exception


# ---------------------------------------------------------------------------
# WorkflowService.create_definition
# ---------------------------------------------------------------------------

class TestCreateDefinition:
    def test_creates_definition(self, db, tenant):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            defn = WorkflowService.create_definition(
                name='Test', trigger_event='loan.submitted',
                config=single_step_config(), tenant=tenant,
            )
        assert defn.pk is not None
        assert defn.version == 1
        assert defn.tenant == tenant

    def test_auto_increments_version(self, db, tenant, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            defn2 = WorkflowService.create_definition(
                name='Loan Approval', trigger_event='loan.submitted',
                config=single_step_config(), tenant=tenant,
            )
        assert defn2.version == 2

    def test_rejects_invalid_config(self, db, tenant):
        with pytest.raises(ValueError):
            WorkflowService.create_definition(
                name='Bad', trigger_event='', config={}, tenant=tenant,
            )


# ---------------------------------------------------------------------------
# WorkflowService.instantiate
# ---------------------------------------------------------------------------

class TestInstantiate:
    def _steps(self, instance):
        return list(WorkflowStep.objects_unscoped.filter(instance=instance).order_by('step_order'))

    def test_creates_instance_and_steps(self, db, tenant, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition,
                entity_type='Loan',
                entity_id='loan-1',
                tenant=tenant,
            )
        assert instance.pk is not None
        assert instance.entity_type == 'Loan'
        assert instance.entity_id == 'loan-1'
        assert WorkflowStep.objects_unscoped.filter(instance=instance).count() == 1

    def test_first_step_activated(self, db, tenant, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='L1', tenant=tenant,
            )
        step = self._steps(instance)[0]
        assert step.status == StepStatus.IN_PROGRESS
        assert step.started_at is not None
        assert instance.status == WorkflowStatus.ACTIVE

    def test_step_assigned_by_role(self, db, tenant, role, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='L2', tenant=tenant,
            )
        step = self._steps(instance)[0]
        assert step.assignee_role == role

    def test_context_stored(self, db, tenant, definition):
        ctx = {'amount': 50000, 'currency': 'ETB'}
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='L3',
                context=ctx, tenant=tenant,
            )
        assert instance.context == ctx

    def test_two_steps_only_first_activated(self, db, tenant, definition_two_steps):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition_two_steps, entity_type='Loan', entity_id='L4', tenant=tenant,
            )
        steps = self._steps(instance)
        assert steps[0].status == StepStatus.IN_PROGRESS
        assert steps[1].status == StepStatus.PENDING


# ---------------------------------------------------------------------------
# WorkflowEngine.evaluate_conditions
# ---------------------------------------------------------------------------

class TestEvaluateConditions:
    def test_empty_conditions_always_true(self):
        assert WorkflowEngine.evaluate_conditions([], {}) is True

    def test_eq_match(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'status', 'operator': 'eq', 'value': 'active'}],
            {'status': 'active'},
        ) is True

    def test_eq_no_match(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'status', 'operator': 'eq', 'value': 'active'}],
            {'status': 'inactive'},
        ) is False

    def test_gt_match(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'amount', 'operator': 'gt', 'value': 1000}],
            {'amount': 5000},
        ) is True

    def test_gt_no_match(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'amount', 'operator': 'gt', 'value': 10000}],
            {'amount': 5000},
        ) is False

    def test_gte_equal(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'amount', 'operator': 'gte', 'value': 5000}],
            {'amount': 5000},
        ) is True

    def test_lte_match(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'amount', 'operator': 'lte', 'value': 10000}],
            {'amount': 5000},
        ) is True

    def test_neq_match(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'type', 'operator': 'neq', 'value': 'flat'}],
            {'type': 'reducing'},
        ) is True

    def test_in_match(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'status', 'operator': 'in', 'value': ['a', 'b']}],
            {'status': 'a'},
        ) is True

    def test_in_no_match(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'status', 'operator': 'in', 'value': ['a', 'b']}],
            {'status': 'c'},
        ) is False

    def test_all_conditions_must_pass(self):
        conditions = [
            {'field': 'amount', 'operator': 'gte', 'value': 1000},
            {'field': 'type', 'operator': 'eq', 'value': 'flat'},
        ]
        assert WorkflowEngine.evaluate_conditions(conditions, {'amount': 5000, 'type': 'flat'}) is True
        assert WorkflowEngine.evaluate_conditions(conditions, {'amount': 5000, 'type': 'reducing'}) is False

    def test_missing_field_returns_false(self):
        assert WorkflowEngine.evaluate_conditions(
            [{'field': 'missing', 'operator': 'eq', 'value': 'x'}],
            {},
        ) is False


# ---------------------------------------------------------------------------
# WorkflowEngine.execute_step — APPROVE
# ---------------------------------------------------------------------------

class TestExecuteStepApprove:
    def _make_instance(self, tenant, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            return WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='X', tenant=tenant,
            )

    def _steps(self, instance):
        return list(WorkflowStep.objects_unscoped.filter(instance=instance).order_by('step_order'))

    def test_approve_completes_step(self, db, tenant, actor, definition):
        instance = self._make_instance(tenant, definition)
        step = self._steps(instance)[0]
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            WorkflowEngine.execute_step(step, StepAction.APPROVE, actor, comments='Looks good')
        step.refresh_from_db()
        assert step.status == StepStatus.COMPLETED
        assert step.actor == actor
        assert step.action_taken == StepAction.APPROVE
        assert step.comments == 'Looks good'
        assert step.completed_at is not None

    def test_approve_completes_workflow_when_no_more_steps(self, db, tenant, actor, definition):
        instance = self._make_instance(tenant, definition)
        step = self._steps(instance)[0]
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            WorkflowEngine.execute_step(step, StepAction.APPROVE, actor)
        instance.refresh_from_db()
        assert instance.status == WorkflowStatus.COMPLETED
        assert instance.completed_at is not None

    def test_approve_advances_to_next_step(self, db, tenant, actor, definition_two_steps):
        instance = self._make_instance(tenant, definition_two_steps)
        first = self._steps(instance)[0]
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            WorkflowEngine.execute_step(first, StepAction.APPROVE, actor)
        steps = self._steps(instance)
        steps[0].refresh_from_db()
        steps[1].refresh_from_db()
        assert steps[0].status == StepStatus.COMPLETED
        assert steps[1].status == StepStatus.IN_PROGRESS
        instance.refresh_from_db()
        assert instance.status == WorkflowStatus.ACTIVE

    def test_approve_rejects_non_in_progress_step(self, db, tenant, actor, definition):
        instance = self._make_instance(tenant, definition)
        step = self._steps(instance)[0]
        step.status = StepStatus.PENDING
        step.save(update_fields=['status'])
        with pytest.raises(ValueError, match="Cannot act"):
            WorkflowEngine.execute_step(step, StepAction.APPROVE, actor)


# ---------------------------------------------------------------------------
# WorkflowEngine.execute_step — REJECT
# ---------------------------------------------------------------------------

class TestExecuteStepReject:
    def _make_instance(self, tenant, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            return WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='Y', tenant=tenant,
            )

    def _steps(self, instance):
        return list(WorkflowStep.objects_unscoped.filter(instance=instance).order_by('step_order'))

    def test_reject_cancels_instance(self, db, tenant, actor, definition):
        instance = self._make_instance(tenant, definition)
        step = self._steps(instance)[0]
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            WorkflowEngine.execute_step(step, StepAction.REJECT, actor, comments='Denied')
        step.refresh_from_db()
        assert step.status == StepStatus.REJECTED
        instance.refresh_from_db()
        assert instance.status == WorkflowStatus.CANCELLED

    def test_reject_emits_workflow_completed_event(self, db, tenant, actor, definition):
        instance = self._make_instance(tenant, definition)
        step = self._steps(instance)[0]
        with patch('django.db.transaction.on_commit', new=lambda fn: fn()):
            with patch('apps.events.tasks.dispatch_event.apply_async') as mock_task:
                WorkflowEngine.execute_step(step, StepAction.REJECT, actor)
        mock_task.assert_called()


# ---------------------------------------------------------------------------
# WorkflowEngine.execute_step — RETURN
# ---------------------------------------------------------------------------

class TestExecuteStepReturn:
    def _steps(self, instance):
        return list(WorkflowStep.objects_unscoped.filter(instance=instance).order_by('step_order'))

    def test_return_reopens_previous_completed_step(self, db, tenant, actor, definition_two_steps):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition_two_steps, entity_type='Loan', entity_id='Z', tenant=tenant,
            )
        steps = self._steps(instance)
        first, second = steps[0], steps[1]
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            # approve first step → second becomes IN_PROGRESS
            WorkflowEngine.execute_step(first, StepAction.APPROVE, actor)

        second.refresh_from_db()
        assert second.status == StepStatus.IN_PROGRESS

        with patch('apps.events.tasks.dispatch_event.apply_async'):
            WorkflowEngine.execute_step(second, StepAction.RETURN, actor, comments='Missing docs')

        second.refresh_from_db()
        assert second.status == StepStatus.RETURNED
        first.refresh_from_db()
        assert first.status == StepStatus.IN_PROGRESS
        assert first.action_taken is None
        assert first.actor is None


# ---------------------------------------------------------------------------
# Conditional step skipping
# ---------------------------------------------------------------------------

class TestConditionalStepSkipping:
    def _steps(self, instance):
        return list(WorkflowStep.objects_unscoped.filter(instance=instance).order_by('step_order'))

    def test_step_skipped_when_condition_fails(self, db, tenant):
        config = {
            'steps': [
                {
                    'order': 1, 'name': 'Senior Review', 'type': 'approval',
                    'conditions': [{'field': 'amount', 'operator': 'gt', 'value': 100000}],
                    'auto_execute': False,
                },
                {
                    'order': 2, 'name': 'Final', 'type': 'approval',
                    'conditions': [],
                    'auto_execute': False,
                },
            ]
        }
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            defn = WorkflowService.create_definition(
                name='Conditional', trigger_event='', config=config, tenant=tenant,
            )
            instance = WorkflowService.instantiate(
                definition=defn, entity_type='Loan', entity_id='C1',
                context={'amount': 50000},  # below threshold
                tenant=tenant,
            )
        steps = self._steps(instance)
        assert steps[0].status == StepStatus.SKIPPED
        assert steps[1].status == StepStatus.IN_PROGRESS

    def test_step_not_skipped_when_condition_passes(self, db, tenant):
        config = {
            'steps': [
                {
                    'order': 1, 'name': 'Senior Review', 'type': 'approval',
                    'conditions': [{'field': 'amount', 'operator': 'gt', 'value': 100000}],
                    'auto_execute': False,
                },
            ]
        }
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            defn = WorkflowService.create_definition(
                name='Conditional2', trigger_event='', config=config, tenant=tenant,
            )
            instance = WorkflowService.instantiate(
                definition=defn, entity_type='Loan', entity_id='C2',
                context={'amount': 200000},  # above threshold
                tenant=tenant,
            )
        step = self._steps(instance)[0]
        assert step.status == StepStatus.IN_PROGRESS


# ---------------------------------------------------------------------------
# Auto-execute steps
# ---------------------------------------------------------------------------

class TestAutoExecute:
    def _steps(self, instance):
        return list(WorkflowStep.objects_unscoped.filter(instance=instance).order_by('step_order'))

    def test_auto_execute_step_completed_immediately(self, db, tenant):
        config = {
            'steps': [
                {
                    'order': 1, 'name': 'Auto Disburse', 'type': 'action',
                    'conditions': [], 'auto_execute': True,
                },
            ]
        }
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            defn = WorkflowService.create_definition(
                name='AutoFlow', trigger_event='', config=config, tenant=tenant,
            )
            instance = WorkflowService.instantiate(
                definition=defn, entity_type='Loan', entity_id='A1', tenant=tenant,
            )
        instance.refresh_from_db()
        step = self._steps(instance)[0]
        assert step.status == StepStatus.COMPLETED
        assert step.action_taken == StepAction.APPROVE
        assert instance.status == WorkflowStatus.COMPLETED

    def test_auto_execute_followed_by_manual_step(self, db, tenant, actor):
        config = {
            'steps': [
                {'order': 1, 'name': 'Auto Check', 'type': 'action', 'conditions': [], 'auto_execute': True},
                {'order': 2, 'name': 'Manual Review', 'type': 'approval', 'conditions': [], 'auto_execute': False},
            ]
        }
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            defn = WorkflowService.create_definition(
                name='AutoThenManual', trigger_event='', config=config, tenant=tenant,
            )
            instance = WorkflowService.instantiate(
                definition=defn, entity_type='Loan', entity_id='A2', tenant=tenant,
            )
        steps = self._steps(instance)
        assert steps[0].status == StepStatus.COMPLETED
        assert steps[1].status == StepStatus.IN_PROGRESS
        instance.refresh_from_db()
        assert instance.status == WorkflowStatus.ACTIVE


# ---------------------------------------------------------------------------
# Role-based step assignment
# ---------------------------------------------------------------------------

class TestRoleAssignment:
    def _first_step(self, instance):
        return WorkflowStep.objects_unscoped.filter(instance=instance).order_by('step_order').first()

    def test_assign_by_role_slug(self, db, tenant, role):
        config = single_step_config(assignee_type='role', assignee_value='loan-officer')
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            defn = WorkflowService.create_definition(
                name='RoleFlow', trigger_event='', config=config, tenant=tenant,
            )
            instance = WorkflowService.instantiate(
                definition=defn, entity_type='Loan', entity_id='R1', tenant=tenant,
            )
        step = self._first_step(instance)
        assert step.assignee_role == role

    def test_assign_by_user_email(self, db, tenant, user):
        Membership.objects.create(tenant=tenant, user=user, status='active')
        config = single_step_config(assignee_type='user', assignee_value='officer@bank.com')
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            defn = WorkflowService.create_definition(
                name='UserFlow', trigger_event='', config=config, tenant=tenant,
            )
            instance = WorkflowService.instantiate(
                definition=defn, entity_type='Loan', entity_id='U1', tenant=tenant,
            )
        step = self._first_step(instance)
        assert step.assignee == user

    def test_missing_role_does_not_raise(self, db, tenant):
        config = single_step_config(assignee_type='role', assignee_value='nonexistent-role')
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            defn = WorkflowService.create_definition(
                name='MissingRole', trigger_event='', config=config, tenant=tenant,
            )
            instance = WorkflowService.instantiate(
                definition=defn, entity_type='Loan', entity_id='M1', tenant=tenant,
            )
        step = self._first_step(instance)
        assert step.assignee_role is None
        assert step.status == StepStatus.IN_PROGRESS


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


def _auth(client, user, tenant):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}',
        HTTP_X_TENANT_ID=str(tenant.id),
    )


@pytest.fixture
def workflow_manager(db, tenant):
    user = User.objects.create_user(email='manager@bank.com', password='pw')
    perm_manage = Permission.objects.create(codename='workflow:manage', description='')
    perm_read = Permission.objects.create(codename='workflow:read', description='')
    role = Role.objects_unscoped.create(tenant=tenant, name='WF Manager', slug='wf-manager')
    RolePermission.objects.create(role=role, permission=perm_manage)
    RolePermission.objects.create(role=role, permission=perm_read)
    Membership.objects.create(tenant=tenant, user=user, status='active')
    RBACService.assign_role(user, tenant, role)
    return user


class TestWorkflowDefinitionAPI:
    def test_create_definition(self, db, tenant, api_client, workflow_manager):
        _auth(api_client, workflow_manager, tenant)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            with patch('django.db.transaction.on_commit', new=lambda fn: None):
                resp = api_client.post('/api/v1/workflow/definitions/', {
                    'name': 'API Def',
                    'trigger_event': 'loan.submitted',
                    'config': single_step_config(),
                }, format='json')
        assert resp.status_code == 201
        assert resp.data['name'] == 'API Def'
        assert resp.data['version'] == 1

    def test_list_definitions(self, db, tenant, api_client, workflow_manager, definition):
        _auth(api_client, workflow_manager, tenant)
        resp = api_client.get('/api/v1/workflow/definitions/')
        assert resp.status_code == 200
        assert len(resp.data['results']) >= 1

    def test_create_rejects_unauthenticated(self, db, api_client):
        resp = api_client.post('/api/v1/workflow/definitions/', {}, format='json')
        assert resp.status_code in (401, 403)


class TestWorkflowInstanceAPI:
    def test_list_instances(self, db, tenant, api_client, workflow_manager, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='I1', tenant=tenant,
            )
        _auth(api_client, workflow_manager, tenant)
        resp = api_client.get('/api/v1/workflow/instances/')
        assert resp.status_code == 200
        assert len(resp.data['results']) >= 1

    def test_retrieve_instance_includes_steps(self, db, tenant, api_client, workflow_manager, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='I2', tenant=tenant,
            )
        _auth(api_client, workflow_manager, tenant)
        resp = api_client.get(f'/api/v1/workflow/instances/{instance.id}/')
        assert resp.status_code == 200
        assert len(resp.data['steps']) == 1


def _first_step(instance):
    return WorkflowStep.objects_unscoped.filter(instance=instance).order_by('step_order').first()


class TestStepActionAPI:
    def test_approve_via_api(self, db, tenant, api_client, workflow_manager, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='S1', tenant=tenant,
            )
        step = _first_step(instance)
        _auth(api_client, workflow_manager, tenant)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            resp = api_client.post(
                f'/api/v1/workflow/steps/{step.id}/action/',
                {'action': 'approve', 'comments': 'All good'},
                format='json',
            )
        assert resp.status_code == 200
        assert resp.data['status'] == StepStatus.COMPLETED

    def test_reject_via_api(self, db, tenant, api_client, workflow_manager, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='S2', tenant=tenant,
            )
        step = _first_step(instance)
        _auth(api_client, workflow_manager, tenant)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            resp = api_client.post(
                f'/api/v1/workflow/steps/{step.id}/action/',
                {'action': 'reject', 'comments': 'Denied'},
                format='json',
            )
        assert resp.status_code == 200
        assert resp.data['status'] == StepStatus.REJECTED

    def test_invalid_action_rejected(self, db, tenant, api_client, workflow_manager, definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=definition, entity_type='Loan', entity_id='S3', tenant=tenant,
            )
        step = _first_step(instance)
        _auth(api_client, workflow_manager, tenant)
        resp = api_client.post(
            f'/api/v1/workflow/steps/{step.id}/action/',
            {'action': 'skip'},
            format='json',
        )
        assert resp.status_code == 400
