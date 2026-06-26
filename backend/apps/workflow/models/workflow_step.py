from django.conf import settings
from django.db import models

from apps.workflow.constants import StepAction, StepStatus, StepType
from core.models import TenantScopedModel


class WorkflowStep(TenantScopedModel):
    instance = models.ForeignKey(
        'workflow.WorkflowInstance',
        on_delete=models.CASCADE,
        related_name='steps',
    )
    step_order = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=200)
    step_type = models.CharField(max_length=20, choices=StepType.choices)
    status = models.CharField(
        max_length=20,
        choices=StepStatus.choices,
        default=StepStatus.PENDING,
        db_index=True,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='workflow_tasks',
    )
    assignee_role = models.ForeignKey(
        'saas.Role',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='workflow_steps',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='workflow_actions',
    )
    action_taken = models.CharField(
        max_length=10,
        choices=StepAction.choices,
        null=True, blank=True,
    )
    comments = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    config = models.JSONField(default=dict)

    class Meta:
        db_table = 'workflow_step'
        unique_together = ('instance', 'step_order')
        ordering = ['step_order']

    def __str__(self):
        return f'{self.name} [{self.status}]'
