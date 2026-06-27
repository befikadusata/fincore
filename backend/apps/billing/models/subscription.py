from django.db import models
from core.models import TenantScopedModel
from apps.billing.constants import SubscriptionStatus, BillingCycle, GatewayProvider


class Subscription(TenantScopedModel):
    plan = models.ForeignKey(
        'saas.Plan', on_delete=models.PROTECT, related_name='subscriptions'
    )
    status = models.CharField(
        max_length=50, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING
    )
    billing_cycle = models.CharField(
        max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY
    )
    gateway_provider = models.CharField(
        max_length=20, choices=GatewayProvider.choices, default=GatewayProvider.CHAPA
    )
    gateway_subscription_id = models.CharField(max_length=255, blank=True, default='')
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'billing_subscription'
        ordering = ['-created_at']
