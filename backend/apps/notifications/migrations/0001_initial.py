import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('saas', '0002_plan_planfeature'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_set', to='saas.tenant')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
                ('event_type', models.CharField(max_length=100)),
                ('channel', models.CharField(choices=[('in_app', 'In-App'), ('email', 'Email'), ('sms', 'SMS')], default='in_app', max_length=20)),
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('entity_type', models.CharField(blank=True, default='', max_length=100)),
                ('entity_id', models.CharField(blank=True, default='', max_length=255)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('read', 'Read'), ('failed', 'Failed')], default='sent', max_length=20)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'db_table': 'notifications_notification',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificationpreference_set', to='saas.tenant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preferences', to=settings.AUTH_USER_MODEL)),
                ('event_type', models.CharField(max_length=100)),
                ('in_app_enabled', models.BooleanField(default=True)),
                ('email_enabled', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'notifications_preference',
                'ordering': ['event_type'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'tenant', 'status'], name='notif_recip_tenant_status_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='notificationpreference',
            unique_together={('tenant', 'user', 'event_type')},
        ),
    ]
