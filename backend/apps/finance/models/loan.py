from decimal import Decimal

from django.db import models
from django.db.models import Q

from apps.finance.constants import LoanStatus, TransactionType, TransactionStatus
from core.models import TenantScopedModel


class Loan(TenantScopedModel):
    product = models.ForeignKey(
        'finance.LoanProduct',
        on_delete=models.PROTECT,
        related_name='loans',
        db_index=True,
    )
    borrower = models.ForeignKey(
        'saas.User',
        on_delete=models.PROTECT,
        related_name='loans',
        db_index=True,
    )
    approved_by = models.ForeignKey(
        'saas.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_loans',
    )

    principal_amount = models.DecimalField(max_digits=19, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=19, decimal_places=2)
    total_amount = models.DecimalField(max_digits=19, decimal_places=2)
    outstanding_balance = models.DecimalField(max_digits=19, decimal_places=2)
    term_months = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='ETB')

    status = models.CharField(
        max_length=20,
        choices=LoanStatus.choices,
        default=LoanStatus.CREATED,
        db_index=True,
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    idempotency_key = models.CharField(max_length=255, blank=True, default='', db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'finance_loan'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'idempotency_key'],
                condition=~Q(idempotency_key=''),
                name='uq_loan_tenant_idempotency_key',
            )
        ]

    def __str__(self):
        return f"Loan {self.pk} | {self.principal_amount} {self.currency} | {self.status}"


class Transaction(TenantScopedModel):
    loan = models.ForeignKey(
        'finance.Loan',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transactions',
        db_index=True,
    )
    wallet = models.ForeignKey(
        'finance.Wallet',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transactions',
        db_index=True,
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
    )
    reference = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True, default='', db_index=True)

    class Meta:
        db_table = 'finance_transaction'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'idempotency_key'],
                condition=~Q(idempotency_key=''),
                name='uq_transaction_tenant_idempotency_key',
            )
        ]

    def __str__(self):
        return f"{self.transaction_type} | {self.amount} | {self.status}"
