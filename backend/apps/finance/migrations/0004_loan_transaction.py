import uuid
import django.db.models.deletion
import django.db.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_loan_product'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('principal_amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('interest_amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('outstanding_balance', models.DecimalField(decimal_places=2, max_digits=19)),
                ('term_months', models.PositiveIntegerField()),
                ('currency', models.CharField(default='ETB', max_length=3)),
                ('status', models.CharField(
                    choices=[
                        ('created', 'Created'),
                        ('submitted', 'Submitted'),
                        ('under_review', 'Under Review'),
                        ('approved', 'Approved'),
                        ('rejected', 'Rejected'),
                        ('disbursed', 'Disbursed'),
                        ('active', 'Active'),
                        ('completed', 'Completed'),
                        ('defaulted', 'Defaulted'),
                        ('returned', 'Returned'),
                    ],
                    db_index=True,
                    default='created',
                    max_length=20,
                )),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('disbursed_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('idempotency_key', models.CharField(blank=True, db_index=True, default='', max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('approved_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='approved_loans',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('borrower', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='loans',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('product', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='loans',
                    to='finance.loanproduct',
                )),
                ('tenant', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)s_set',
                    to='saas.tenant',
                )),
            ],
            options={
                'db_table': 'finance_loan',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='loan',
            constraint=models.UniqueConstraint(
                condition=~django.db.models.Q(idempotency_key=''),
                fields=['tenant', 'idempotency_key'],
                name='uq_loan_tenant_idempotency_key',
            ),
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('transaction_type', models.CharField(
                    choices=[
                        ('disbursement', 'Disbursement'),
                        ('repayment', 'Repayment'),
                        ('fee', 'Fee'),
                        ('penalty', 'Penalty'),
                        ('adjustment', 'Adjustment'),
                        ('transfer', 'Transfer'),
                    ],
                    max_length=20,
                )),
                ('amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                        ('reversed', 'Reversed'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('reference', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('idempotency_key', models.CharField(blank=True, db_index=True, default='', max_length=255)),
                ('loan', models.ForeignKey(
                    blank=True,
                    db_index=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='transactions',
                    to='finance.loan',
                )),
                ('wallet', models.ForeignKey(
                    blank=True,
                    db_index=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='transactions',
                    to='finance.wallet',
                )),
                ('tenant', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)s_set',
                    to='saas.tenant',
                )),
            ],
            options={
                'db_table': 'finance_transaction',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='transaction',
            constraint=models.UniqueConstraint(
                condition=~django.db.models.Q(idempotency_key=''),
                fields=['tenant', 'idempotency_key'],
                name='uq_transaction_tenant_idempotency_key',
            ),
        ),
    ]
