from decimal import Decimal

from django.db import models

from apps.finance.constants import RepaymentStatus
from core.models import TenantScopedModel


class RepaymentSchedule(TenantScopedModel):
    loan = models.ForeignKey(
        'finance.Loan',
        on_delete=models.PROTECT,
        related_name='schedule',
        db_index=True,
    )
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField(db_index=True)

    principal_amount = models.DecimalField(max_digits=19, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=19, decimal_places=2)
    total_amount = models.DecimalField(max_digits=19, decimal_places=2)

    amount_paid = models.DecimalField(max_digits=19, decimal_places=2, default=Decimal('0.00'))
    penalty_amount = models.DecimalField(max_digits=19, decimal_places=2, default=Decimal('0.00'))

    status = models.CharField(
        max_length=20,
        choices=RepaymentStatus.choices,
        default=RepaymentStatus.PENDING,
        db_index=True,
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'finance_repayment_schedule'
        ordering = ['installment_number']
        unique_together = ('loan', 'installment_number')

    def __str__(self):
        return f"Installment {self.installment_number} | {self.total_amount} | {self.status}"
