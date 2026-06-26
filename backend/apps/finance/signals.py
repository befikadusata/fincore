from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.finance.constants import AccountType, AccountCategory

SYSTEM_CHART_OF_ACCOUNTS = [
    ('1000', 'Cash',                      AccountType.ASSET,     AccountCategory.CASH),
    ('1100', 'Loan Receivable',           AccountType.ASSET,     AccountCategory.LOAN_RECEIVABLE),
    ('1200', 'Interest Receivable',       AccountType.ASSET,     AccountCategory.INTEREST_RECEIVABLE),
    ('1300', 'Fee Receivable',            AccountType.ASSET,     AccountCategory.FEE_RECEIVABLE),
    ('2000', 'Borrower Wallets Payable',  AccountType.LIABILITY, AccountCategory.BORROWER_WALLET),
    ('4000', 'Interest Revenue',          AccountType.REVENUE,   AccountCategory.INTEREST_REVENUE),
    ('4100', 'Fee Revenue',               AccountType.REVENUE,   AccountCategory.FEE_REVENUE),
    ('4200', 'Penalty Revenue',           AccountType.REVENUE,   AccountCategory.PENALTY_REVENUE),
]


@receiver(post_save, sender='saas.Tenant')
def create_chart_of_accounts(sender, instance, created, **kwargs):
    if not created:
        return

    from apps.finance.models.account import Account

    Account.objects_unscoped.bulk_create([
        Account(
            tenant=instance,
            code=code,
            name=name,
            account_type=account_type,
            category=category,
            is_system=True,
        )
        for code, name, account_type, category in SYSTEM_CHART_OF_ACCOUNTS
    ])
