from django.db import migrations


SUBSCRIPTIONS = [
    ('loan.submitted',    'apps.workflow.handlers.handle_loan_submitted'),
    ('workflow.completed', 'apps.workflow.handlers.handle_workflow_completed'),
    ('loan.approved',     'apps.finance.handlers.handle_loan_approved'),
]


def create_subscriptions(apps, schema_editor):
    EventSubscription = apps.get_model('events', 'EventSubscription')
    for event_type, handler_path in SUBSCRIPTIONS:
        EventSubscription.objects.get_or_create(
            event_type=event_type,
            handler_path=handler_path,
            defaults={'is_active': True},
        )


def remove_subscriptions(apps, schema_editor):
    EventSubscription = apps.get_model('events', 'EventSubscription')
    for event_type, handler_path in SUBSCRIPTIONS:
        EventSubscription.objects.filter(
            event_type=event_type,
            handler_path=handler_path,
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_subscriptions, remove_subscriptions),
    ]
