import logging

from django.db import transaction
from django.utils import timezone

from apps.workflow.constants import StepStatus, WorkflowStatus
from apps.workflow.models import WorkflowDefinition, WorkflowInstance, WorkflowStep

logger = logging.getLogger(__name__)

_VALID_OPERATORS = {'eq', 'neq', 'gt', 'lt', 'gte', 'lte', 'in', 'contains'}


def _validate_config(config: dict):
    from apps.workflow.constants import StepType
    if not isinstance(config, dict):
        raise ValueError("config must be a JSON object")
    steps = config.get('steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError("config.steps must be a non-empty list")
    orders = set()
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"step[{i}] must be an object")
        for key in ('order', 'name', 'type'):
            if key not in step:
                raise ValueError(f"step[{i}] missing required key '{key}'")
        order = step['order']
        if order in orders:
            raise ValueError(f"Duplicate step order: {order}")
        orders.add(order)
        if step['type'] not in StepType.values:
            raise ValueError(f"step[{i}] has invalid type '{step['type']}'")
        for j, cond in enumerate(step.get('conditions', [])):
            if not isinstance(cond, dict):
                raise ValueError(f"step[{i}].conditions[{j}] must be an object")
            for key in ('field', 'operator', 'value'):
                if key not in cond:
                    raise ValueError(f"step[{i}].conditions[{j}] missing key '{key}'")
            if cond['operator'] not in _VALID_OPERATORS:
                raise ValueError(f"Invalid operator '{cond['operator']}'")


class WorkflowService:
    @staticmethod
    @transaction.atomic
    def create_definition(
        name: str,
        trigger_event: str,
        config: dict,
        tenant,
    ) -> WorkflowDefinition:
        _validate_config(config)
        last = WorkflowDefinition.objects_unscoped.filter(
            tenant=tenant, name=name
        ).order_by('-version').first()
        version = (last.version + 1) if last else 1
        return WorkflowDefinition.objects_unscoped.create(
            tenant=tenant,
            name=name,
            trigger_event=trigger_event,
            config=config,
            version=version,
        )

    @staticmethod
    @transaction.atomic
    def instantiate(
        definition: WorkflowDefinition,
        entity_type: str,
        entity_id: str,
        context: dict = None,
        tenant=None,
    ) -> WorkflowInstance:
        if tenant is None:
            tenant = definition.tenant

        instance = WorkflowInstance.objects_unscoped.create(
            tenant=tenant,
            definition=definition,
            entity_type=entity_type,
            entity_id=str(entity_id),
            status=WorkflowStatus.PENDING,
            context=context or {},
        )

        steps_config = sorted(definition.config['steps'], key=lambda s: s['order'])
        WorkflowStep.objects.bulk_create([
            WorkflowStep(
                tenant=tenant,
                instance=instance,
                step_order=sc['order'],
                name=sc['name'],
                step_type=sc['type'],
                status=StepStatus.PENDING,
                config=sc,
            )
            for sc in steps_config
        ])

        WorkflowService.advance(instance)
        return instance

    @staticmethod
    @transaction.atomic
    def advance(instance: WorkflowInstance):
        """Activate the next applicable pending step, or complete the workflow."""
        from apps.workflow.services.workflow_engine import WorkflowEngine

        pending = list(
            WorkflowStep.objects_unscoped.filter(
                instance=instance, status=StepStatus.PENDING,
            ).order_by('step_order')
        )

        for step in pending:
            conditions = step.config.get('conditions', [])
            if not WorkflowEngine.evaluate_conditions(conditions, instance.context):
                step.status = StepStatus.SKIPPED
                step.completed_at = timezone.now()
                step.save(update_fields=['status', 'completed_at', 'updated_at'])
                continue

            if step.config.get('auto_execute'):
                WorkflowEngine.auto_execute(step)
                continue

            step.status = StepStatus.IN_PROGRESS
            step.started_at = timezone.now()
            WorkflowEngine.assign_step(step, step.config, instance.tenant)
            step.save()
            instance.status = WorkflowStatus.ACTIVE
            instance.save(update_fields=['status', 'updated_at'])
            _emit_step_assigned(step, instance)
            return

        # All pending steps exhausted — workflow done
        instance.status = WorkflowStatus.COMPLETED
        instance.completed_at = timezone.now()
        instance.save(update_fields=['status', 'completed_at', 'updated_at'])
        _emit_workflow_completed(instance)


def _emit_step_assigned(step: WorkflowStep, instance: WorkflowInstance):
    try:
        from apps.events.constants import EventType
        from apps.events.services.event_bus import EventBus
        EventBus.emit(
            event_type=EventType.WORKFLOW_STEP_ASSIGNED,
            entity_type='WorkflowStep',
            entity_id=str(step.id),
            payload={
                'instance_id': str(instance.id),
                'entity_type': instance.entity_type,
                'entity_id': instance.entity_id,
                'step_name': step.name,
                'assignee_id': str(step.assignee_id) if step.assignee_id else None,
                'assignee_role_id': str(step.assignee_role_id) if step.assignee_role_id else None,
            },
            tenant=instance.tenant,
        )
    except Exception:
        logger.debug('Failed to emit workflow.step_assigned for step %s', step.id)


def _emit_workflow_completed(instance: WorkflowInstance):
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
                'outcome': 'completed',
            },
            tenant=instance.tenant,
        )
    except Exception:
        logger.debug('Failed to emit workflow.completed for instance %s', instance.id)
