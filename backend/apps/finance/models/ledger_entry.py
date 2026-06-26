import uuid
from django.db import models
from core.models import TenantScopedModel
from apps.finance.constants import EntryType


class LedgerEntry(TenantScopedModel):
    account = models.ForeignKey(
        'finance.Account',
        on_delete=models.PROTECT,
        related_name='entries',
    )
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    reference = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    # Nullable UUID so it can reference any future Transaction model
    transaction_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'finance_ledger_entry'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entry_type} {self.amount} -> {self.account.code} [{self.reference}]"
