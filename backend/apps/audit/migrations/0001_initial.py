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
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('actor_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('actor_type', models.CharField(
                    choices=[('user', 'User'), ('system', 'System'), ('celery', 'Celery')],
                    default='user',
                    max_length=20,
                )),
                ('action', models.CharField(
                    choices=[
                        ('create', 'Create'),
                        ('update', 'Update'),
                        ('delete', 'Delete'),
                        ('status_change', 'Status Change'),
                        ('login', 'Login'),
                        ('logout', 'Logout'),
                    ],
                    db_index=True,
                    max_length=30,
                )),
                ('entity_type', models.CharField(db_index=True, max_length=100)),
                ('entity_id', models.CharField(blank=True, db_index=True, max_length=100)),
                ('changes', models.JSONField(default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('tenant', models.ForeignKey(
                    blank=True,
                    db_index=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='audit_logs',
                    to='saas.tenant',
                )),
            ],
            options={
                'db_table': 'audit_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['entity_type', 'entity_id'], name='audit_log_entity_type_entity_id_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['tenant', 'action'], name='audit_log_tenant_action_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['actor_id', 'created_at'], name='audit_log_actor_id_created_at_idx'),
        ),
    ]
