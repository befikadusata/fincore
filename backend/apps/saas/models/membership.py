import uuid
from django.db import models
from apps.saas.models.tenant import Tenant
from apps.saas.models.user import User


class Membership(models.Model):
    """Join model for User and Tenant multi-tenancy."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saas_membership'
        unique_together = ('user', 'tenant')
