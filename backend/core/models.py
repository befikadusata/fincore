import uuid
from django.db import models
from core.managers import TenantManager


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class TenantScopedModel(BaseModel):
    tenant = models.ForeignKey(
        'saas.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        db_index=True
    )

    objects = TenantManager()
    objects_unscoped = models.Manager()

    class Meta:
        abstract = True


class IdempotencyRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=255, db_index=True)
    user = models.ForeignKey(
        'saas.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True
    )
    response_status = models.IntegerField()
    response_body = models.TextField()
    response_content_type = models.CharField(max_length=100, default='application/json')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'core_idempotency_record'
        constraints = [
            models.UniqueConstraint(fields=['key', 'user'], name='uq_idemp_key_user'),
        ]
        ordering = ['-created_at']
