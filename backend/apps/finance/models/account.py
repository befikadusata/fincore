from django.db import models
from core.models import TenantScopedModel
from apps.finance.constants import AccountType, AccountCategory


class Account(TenantScopedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    category = models.CharField(
        max_length=50, choices=AccountCategory.choices, blank=True, default=''
    )
    is_system = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'finance_account'
        unique_together = ('tenant', 'code')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"
