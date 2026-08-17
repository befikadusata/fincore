from django.db import migrations, models


def dedupe_plans_by_slug(apps, schema_editor):
    """
    Plans were tenant-scoped, so the same slug could exist once per tenant.
    The catalogue is global from here on and slug becomes unique, so collapse
    each slug group onto its oldest plan and repoint everything that referenced
    a duplicate. Subscription.plan is PROTECT, so repointing must happen before
    the duplicates are deleted.
    """
    Plan = apps.get_model('saas', 'Plan')
    PlanFeature = apps.get_model('saas', 'PlanFeature')
    Subscription = apps.get_model('billing', 'Subscription')

    slugs = Plan.objects.values_list('slug', flat=True).distinct()
    for slug in slugs:
        plans = list(Plan.objects.filter(slug=slug).order_by('created_at'))
        if len(plans) < 2:
            continue

        canonical, duplicates = plans[0], plans[1:]
        duplicate_ids = [p.id for p in duplicates]

        Subscription.objects.filter(plan_id__in=duplicate_ids).update(plan_id=canonical.id)

        # Carry over any feature the canonical plan does not already declare.
        existing = set(
            PlanFeature.objects.filter(plan_id=canonical.id).values_list('codename', flat=True)
        )
        for feature in PlanFeature.objects.filter(plan_id__in=duplicate_ids):
            if feature.codename not in existing:
                feature.plan_id = canonical.id
                feature.save(update_fields=['plan'])
                existing.add(feature.codename)

        # Remaining duplicate features cascade with their plans.
        Plan.objects.filter(id__in=duplicate_ids).delete()


def noop_reverse(apps, schema_editor):
    """Deduplication is not reversible; the reverse path only restores schema."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('saas', '0003_encrypt_user_name_fields'),
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='plan',
            unique_together=set(),
        ),
        migrations.RunPython(dedupe_plans_by_slug, noop_reverse),
        migrations.RemoveField(
            model_name='plan',
            name='tenant',
        ),
        migrations.AlterField(
            model_name='plan',
            name='slug',
            field=models.SlugField(unique=True),
        ),
        migrations.AlterModelOptions(
            name='plan',
            options={'ordering': ['-created_at']},
        ),
    ]
