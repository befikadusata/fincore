from django.db import models
from core.models import TenantScopedModel
from apps.billing.constants import InvoiceStatus


class Invoice(TenantScopedModel):
    subscription = models.ForeignKey(
        'billing.Subscription', on_delete=models.CASCADE, related_name='invoices'
    )
    invoice_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=50, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    gateway_invoice_id = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'billing_invoice'
        ordering = ['-created_at']
