import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('saas', '0002_plan_planfeature'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(
                    choices=[
                        ('trialing', 'Trialing'),
                        ('active', 'Active'),
                        ('past_due', 'Past Due'),
                        ('cancelled', 'Cancelled'),
                        ('expired', 'Expired'),
                    ],
                    default='trialing',
                    max_length=50,
                )),
                ('billing_cycle', models.CharField(
                    choices=[
                        ('monthly', 'Monthly'),
                        ('quarterly', 'Quarterly'),
                        ('annually', 'Annually'),
                    ],
                    default='monthly',
                    max_length=20,
                )),
                ('gateway_provider', models.CharField(
                    choices=[('chapa', 'Chapa'), ('stripe', 'Stripe')],
                    default='chapa',
                    max_length=20,
                )),
                ('gateway_subscription_id', models.CharField(blank=True, default='', max_length=255)),
                ('current_period_start', models.DateTimeField(blank=True, null=True)),
                ('current_period_end', models.DateTimeField(blank=True, null=True)),
                ('trial_end', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('plan', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='subscriptions',
                    to='saas.plan',
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscription_set',
                    to='saas.tenant',
                    db_index=True,
                )),
            ],
            options={
                'db_table': 'billing_subscription',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('invoice_number', models.CharField(max_length=100, unique=True)),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'Draft'),
                        ('issued', 'Issued'),
                        ('paid', 'Paid'),
                        ('overdue', 'Overdue'),
                        ('cancelled', 'Cancelled'),
                        ('refunded', 'Refunded'),
                    ],
                    default='draft',
                    max_length=50,
                )),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('currency', models.CharField(max_length=3)),
                ('due_date', models.DateField()),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('gateway_invoice_id', models.CharField(blank=True, default='', max_length=255)),
                ('subscription', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invoices',
                    to='billing.subscription',
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invoice_set',
                    to='saas.tenant',
                    db_index=True,
                )),
            ],
            options={
                'db_table': 'billing_invoice',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                        ('refunded', 'Refunded'),
                    ],
                    default='pending',
                    max_length=50,
                )),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('currency', models.CharField(max_length=3)),
                ('gateway_reference', models.CharField(max_length=255)),
                ('gateway_provider', models.CharField(
                    choices=[('chapa', 'Chapa'), ('stripe', 'Stripe')],
                    max_length=20,
                )),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('idempotency_key', models.CharField(blank=True, default='', max_length=255)),
                ('invoice', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments',
                    to='billing.invoice',
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='paymentrecord_set',
                    to='saas.tenant',
                    db_index=True,
                )),
            ],
            options={
                'db_table': 'billing_payment_record',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['tenant', 'status'], name='billing_sub_tenant_status_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['tenant', 'status'], name='billing_inv_tenant_status_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentrecord',
            index=models.Index(fields=['gateway_reference'], name='billing_pay_gateway_ref_idx'),
        ),
    ]
