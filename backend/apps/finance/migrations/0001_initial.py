import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('saas', '0002_plan_planfeature'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('code', models.CharField(max_length=20)),
                ('account_type', models.CharField(
                    choices=[
                        ('asset', 'Asset'),
                        ('liability', 'Liability'),
                        ('equity', 'Equity'),
                        ('revenue', 'Revenue'),
                        ('expense', 'Expense'),
                    ],
                    max_length=20,
                )),
                ('category', models.CharField(
                    blank=True,
                    choices=[
                        ('cash', 'Cash'),
                        ('loan_receivable', 'Loan Receivable'),
                        ('interest_receivable', 'Interest Receivable'),
                        ('fee_receivable', 'Fee Receivable'),
                        ('borrower_wallet', 'Borrower Wallet'),
                        ('interest_revenue', 'Interest Revenue'),
                        ('fee_revenue', 'Fee Revenue'),
                        ('penalty_revenue', 'Penalty Revenue'),
                    ],
                    default='',
                    max_length=50,
                )),
                ('is_system', models.BooleanField(default=False)),
                ('description', models.TextField(blank=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)s_set',
                    to='saas.tenant',
                    db_index=True,
                )),
            ],
            options={
                'db_table': 'finance_account',
                'ordering': ['code'],
                'unique_together': {('tenant', 'code')},
            },
        ),
        migrations.CreateModel(
            name='LedgerEntry',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('entry_type', models.CharField(
                    choices=[('debit', 'Debit'), ('credit', 'Credit')],
                    max_length=10,
                )),
                ('amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('reference', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('transaction_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('account', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='entries',
                    to='finance.account',
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)s_set',
                    to='saas.tenant',
                    db_index=True,
                )),
            ],
            options={
                'db_table': 'finance_ledger_entry',
                'ordering': ['-created_at'],
            },
        ),
    ]
