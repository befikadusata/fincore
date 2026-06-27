from django.db import migrations


SUBSCRIPTIONS = [
    ('loan.approved',               'apps.notifications.handlers.handle_loan_approved'),
    ('loan.disbursed',              'apps.notifications.handlers.handle_loan_disbursed'),
    ('repayment.due_soon',          'apps.notifications.handlers.handle_repayment_due_soon'),
    ('workflow.step_assigned',      'apps.notifications.handlers.handle_workflow_step_assigned'),
    ('subscription.payment_failed', 'apps.notifications.handlers.handle_subscription_payment_failed'),
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
        ('notifications', '0001_initial'),
        ('events', '0002_loan_workflow_subscriptions'),
    ]

    operations = [
        migrations.RunPython(create_subscriptions, remove_subscriptions),
    ]
