from django.db import models

from core.models import TenantScopedModel


class WorkflowDefinition(TenantScopedModel):
    name = models.CharField(max_length=200)
    trigger_event = models.CharField(max_length=100, blank=True)
    config = models.JSONField()
    version = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'workflow_definition'
        unique_together = ('tenant', 'name', 'version')

    def __str__(self):
        return f'{self.name} v{self.version}'
