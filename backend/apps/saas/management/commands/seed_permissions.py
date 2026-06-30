from django.core.management.base import BaseCommand
from apps.saas.models import Permission

PERMISSIONS = [
    ('audit:read', 'View audit logs'),
    ('events:read', 'View events'),
    ('events:manage', 'Manage events'),
    ('loan_products:manage', 'Create and manage loan products'),
    ('loans:manage', 'Create, approve, and manage loans'),
    ('roles:assign_permissions', 'Assign permissions to roles'),
    ('roles:assign_members', 'Assign members to roles'),
    ('workflow:read', 'View workflow definitions and tasks'),
    ('workflow:manage', 'Create and manage workflow definitions'),
]


class Command(BaseCommand):
    help = 'Seed the permissions table with all application codenames'

    def handle(self, *args, **options):
        created = 0
        for codename, description in PERMISSIONS:
            _, was_created = Permission.objects.get_or_create(
                codename=codename,
                defaults={'description': description},
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(f'Done — {created} created, {len(PERMISSIONS) - created} already existed')
        )
