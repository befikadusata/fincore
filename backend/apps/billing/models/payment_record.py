from django.db import models
from core.models import TenantScopedModel
from apps.billing.constants import PaymentStatus, GatewayProvider


class PaymentRecord(TenantScopedModel):
    invoice = models.ForeignKey(
        'billing.Invoice', on_delete=models.CASCADE, related_name='payments'
    )
    status = models.CharField(
        max_length=50, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    gateway_reference = models.CharField(max_length=255)
    gateway_provider = models.CharField(max_length=20, choices=GatewayProvider.choices)
    metadata = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'billing_payment_record'
        ordering = ['-created_at']
