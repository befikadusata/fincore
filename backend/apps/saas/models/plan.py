from django.db import models
from core.models import TenantScopedModel, BaseModel


class Plan(TenantScopedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    monthly_price = models.IntegerField(default=0)
    annual_price = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default='ETB')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'saas_plan'
        unique_together = ('tenant', 'slug')


class PlanFeature(BaseModel):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'saas_plan_feature'
        unique_together = ('plan', 'codename')
