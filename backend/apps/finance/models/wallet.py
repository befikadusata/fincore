from decimal import Decimal

from django.db import models

from apps.finance.constants import WalletType, WalletStatus
from core.models import TenantScopedModel


class Wallet(TenantScopedModel):
    owner = models.ForeignKey(
        'saas.User',
        on_delete=models.PROTECT,
        related_name='wallets',
        db_index=True,
    )
    account = models.OneToOneField(
        'finance.Account',
        on_delete=models.PROTECT,
        related_name='wallet',
        null=True,
        blank=True,
    )
    wallet_type = models.CharField(
        max_length=20,
        choices=WalletType.choices,
        default=WalletType.PERSONAL,
    )
    currency = models.CharField(max_length=3, default='ETB')
    balance = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    status = models.CharField(
        max_length=20,
        choices=WalletStatus.choices,
        default=WalletStatus.ACTIVE,
    )

    class Meta:
        db_table = 'finance_wallet'
        unique_together = ('tenant', 'owner', 'wallet_type')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.owner_id} | {self.wallet_type} | {self.balance} {self.currency}"
