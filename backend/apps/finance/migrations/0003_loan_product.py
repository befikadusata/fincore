import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_wallet'),
        ('saas', '0002_plan_planfeature'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoanProduct',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('interest_type', models.CharField(
                    choices=[
                        ('flat', 'Flat'),
                        ('reducing_balance', 'Reducing Balance'),
                        ('compound', 'Compound'),
                    ],
                    max_length=30,
                )),
                ('interest_rate', models.DecimalField(decimal_places=4, max_digits=7)),
                ('compounding_periods_per_year', models.PositiveSmallIntegerField(default=12)),
                ('min_term_months', models.PositiveIntegerField()),
                ('max_term_months', models.PositiveIntegerField()),
                ('min_amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('max_amount', models.DecimalField(decimal_places=2, max_digits=19)),
                ('currency', models.CharField(default='ETB', max_length=3)),
                ('fees_config', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('tenant', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)s_set',
                    to='saas.tenant',
                )),
            ],
            options={
                'db_table': 'finance_loan_product',
                'ordering': ['name'],
            },
        ),
    ]
