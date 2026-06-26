import logging

from django.db import transaction
from django.utils import timezone

from apps.workflow.constants import StepAction, StepStatus, WorkflowStatus
from apps.workflow.models import WorkflowInstance, WorkflowStep

logger = logging.getLogger(__name__)


class WorkflowEngine:
    @staticmethod
    @transaction.atomic
    def execute_step(step: WorkflowStep, action: str, actor, comments: str = '') -> WorkflowStep:
        if step.status != StepStatus.IN_PROGRESS:
            raise ValueError(f"Cannot act on step with status '{step.status}'")
        if action not in StepAction.values:
            raise ValueError(f"Invalid action '{action}'")

        step.actor = actor
        step.action_taken = action
        step.comments = comments
        step.completed_at = timezone.now()

        if action == StepAction.APPROVE:
            step.status = StepStatus.COMPLETED
            step.save()
            from apps.workflow.services.workflow_service import WorkflowService
            WorkflowService.advance(step.instance)

        elif action == StepAction.REJECT:
            step.status = StepStatus.REJECTED
            step.save()
            instance = step.instance
            instance.status = WorkflowStatus.CANCELLED
            instance.completed_at = timezone.now()
            instance.save(update_fields=['status', 'completed_at', 'updated_at'])
            _emit_workflow_completed(instance, outcome='rejected')

        elif action == StepAction.RETURN:
            step.status = StepStatus.RETURNED
            step.save()
            prev = WorkflowStep.objects_unscoped.filter(
                instance=step.instance,
                status=StepStatus.COMPLETED,
            ).order_by('-step_order').first()
            if prev:
                prev.status = StepStatus.IN_PROGRESS
                prev.started_at = timezone.now()
                prev.action_taken = None
                prev.actor = None
                prev.completed_at = None
                prev.save(update_fields=[
                    'status', 'started_at', 'action_taken', 'actor', 'completed_at', 'updated_at',
                ])

        return step

    @staticmethod
    def evaluate_conditions(conditions: list, context: dict) -> bool:
        for cond in conditions:
            field = cond['field']
            operator = cond['operator']
            expected = cond['value']
            actual = context.get(field)

            try:
                if operator == 'eq' and actual != expected:
                    return False
                elif operator == 'neq' and actual == expected:
                    return False
                elif operator == 'gt' and not (actual > expected):
                    return False
                elif operator == 'lt' and not (actual < expected):
                    return False
                elif operator == 'gte' and not (actual >= expected):
                    return False
                elif operator == 'lte' and not (actual <= expected):
                    return False
                elif operator == 'in' and actual not in expected:
                    return False
                elif operator == 'contains' and expected not in actual:
                    return False
            except (TypeError, ValueError):
                return False

        return True

    @staticmethod
    def assign_step(step: WorkflowStep, step_config: dict, tenant) -> WorkflowStep:
        assignee_type = step_config.get('assignee_type')
        assignee_value = step_config.get('assignee_value')

        if not assignee_type or not assignee_value:
            return step

        if assignee_type == 'role':
            from apps.saas.models import Role
            try:
                role = Role.objects_unscoped.get(tenant=tenant, slug=assignee_value)
                step.assignee_role = role
            except Role.DoesNotExist:
                logger.warning('Role slug=%s not found in tenant %s', assignee_value, tenant.id)

        elif assignee_type == 'user':
            from apps.saas.models import User
            try:
                step.assignee = User.objects.get(email=assignee_value)
            except User.DoesNotExist:
                logger.warning('User email=%s not found', assignee_value)

        return step

    @staticmethod
    def auto_execute(step: WorkflowStep) -> WorkflowStep:
        step.status = StepStatus.COMPLETED
        step.action_taken = StepAction.APPROVE
        step.started_at = timezone.now()
        step.completed_at = timezone.now()
        step.save(update_fields=['status', 'action_taken', 'started_at', 'completed_at', 'updated_at'])
        return step


def _emit_workflow_completed(instance: WorkflowInstance, outcome: str = 'completed'):
    try:
        from apps.events.constants import EventType
        from apps.events.services.event_bus import EventBus
        EventBus.emit(
            event_type=EventType.WORKFLOW_COMPLETED,
            entity_type=instance.entity_type,
            entity_id=instance.entity_id,
            payload={
                'instance_id': str(instance.id),
                'definition_id': str(instance.definition_id),
                'definition_name': instance.definition.name,
                'outcome': outcome,
            },
            tenant=instance.tenant,
        )
    except Exception:
        logger.debug('Failed to emit workflow.completed for instance %s', instance.id)
