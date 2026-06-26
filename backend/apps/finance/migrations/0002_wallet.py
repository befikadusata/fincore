import uuid
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('wallet_type', models.CharField(
                    choices=[
                        ('personal', 'Personal'),
                        ('business', 'Business'),
                        ('escrow', 'Escrow'),
                    ],
                    default='personal',
                    max_length=20,
                )),
                ('currency', models.CharField(default='ETB', max_length=3)),
                ('balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=19)),
                ('status', models.CharField(
                    choices=[
                        ('active', 'Active'),
                        ('frozen', 'Frozen'),
                        ('closed', 'Closed'),
                    ],
                    default='active',
                    max_length=20,
                )),
                ('account', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='wallet',
                    to='finance.account',
                )),
                ('owner', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='wallets',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('tenant', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)s_set',
                    to='saas.tenant',
                )),
            ],
            options={
                'db_table': 'finance_wallet',
                'ordering': ['-created_at'],
                'unique_together': {('tenant', 'owner', 'wallet_type')},
            },
        ),
    ]
