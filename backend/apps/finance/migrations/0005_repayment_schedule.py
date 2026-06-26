import uuid
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0004_loan_transaction'),
    ]

    operations = [
        migrations.CreateModel(
            name='RepaymentSchedule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('installment_number', models.PositiveIntegerField()),
                ('due_date', models.DateField(db_index=True)),
                ('principal_amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('interest_amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('amount_paid', models.DecimalField(
                    decimal_places=2, default=Decimal('0.00'), max_digits=19
                )),
                ('penalty_amount', models.DecimalField(
                    decimal_places=2, default=Decimal('0.00'), max_digits=19
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('paid', 'Paid'),
                        ('partial', 'Partial'),
                        ('overdue', 'Overdue'),
                        ('waived', 'Waived'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('loan', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='schedule',
                    to='finance.loan',
                )),
                ('tenant', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)s_set',
                    to='saas.tenant',
                )),
            ],
            options={
                'db_table': 'finance_repayment_schedule',
                'ordering': ['installment_number'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='repaymentschedule',
            unique_together={('loan', 'installment_number')},
        ),
    ]
