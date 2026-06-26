import uuid
from django.db import models
from apps.saas.models.tenant import Tenant
from apps.saas.models.membership import Membership

from core.models import TenantScopedModel

class Role(TenantScopedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    membership = models.ManyToManyField(Membership, related_name='roles', db_table='saas_membership_roles')

    class Meta:
        db_table = 'saas_role'
        unique_together = ('tenant', 'slug')
