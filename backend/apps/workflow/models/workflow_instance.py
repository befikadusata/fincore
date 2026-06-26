from django.db import models

from apps.workflow.constants import WorkflowStatus
from core.models import TenantScopedModel


class WorkflowInstance(TenantScopedModel):
    definition = models.ForeignKey(
        'workflow.WorkflowDefinition',
        on_delete=models.PROTECT,
        related_name='instances',
    )
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=100, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.PENDING,
        db_index=True,
    )
    context = models.JSONField(default=dict)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'workflow_instance'
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f'{self.definition.name} [{self.status}] for {self.entity_type}:{self.entity_id}'
