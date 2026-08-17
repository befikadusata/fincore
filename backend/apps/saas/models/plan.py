from django.db import models
from core.models import BaseModel


class Plan(BaseModel):
    """
    The subscription plan catalogue. Plans are platform-owned and global, not
    tenant-scoped: the platform sells them to tenants, so a tenant selects a
    plan rather than defining one. Tenant ownership lives on Subscription.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    monthly_price = models.IntegerField(default=0)
    annual_price = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default='ETB')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'saas_plan'
        ordering = ['-created_at']


class PlanFeature(BaseModel):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'saas_plan_feature'
        unique_together = ('plan', 'codename')
