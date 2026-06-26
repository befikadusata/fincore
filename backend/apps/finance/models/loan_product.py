from django.db import models

from apps.finance.constants import InterestType
from core.models import TenantScopedModel


class LoanProduct(TenantScopedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    interest_type = models.CharField(max_length=30, choices=InterestType.choices)
    # Annual interest rate as a percentage (e.g. 18.00 = 18% p.a.)
    interest_rate = models.DecimalField(max_digits=7, decimal_places=4)
    # For compound products: how many times per year interest compounds (e.g. 12 = monthly)
    compounding_periods_per_year = models.PositiveSmallIntegerField(default=12)

    min_term_months = models.PositiveIntegerField()
    max_term_months = models.PositiveIntegerField()

    min_amount = models.DecimalField(max_digits=19, decimal_places=2)
    max_amount = models.DecimalField(max_digits=19, decimal_places=2)

    currency = models.CharField(max_length=3, default='ETB')

    # Flexible fee config: {"origination_fee_pct": 2.0, "insurance_fee_pct": 0.5, ...}
    fees_config = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'finance_loan_product'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.interest_type} {self.interest_rate}%)"
