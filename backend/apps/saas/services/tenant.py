from apps.saas.models import Tenant, Membership, Role, Permission, RolePermission
from core.middleware.tenant import set_current_tenant
from django.db import transaction


class TenantService:
    @staticmethod
    @transaction.atomic
    def create_tenant(name: str, slug: str, owner_user) -> Tenant:
        tenant = Tenant.objects.create(name=name, slug=slug)

        membership = Membership.objects.create(
            user=owner_user,
            tenant=tenant,
            status='active',
        )

        # Create an Owner role with all permissions and assign it to the owner
        owner_role, _ = Role.objects.get_or_create(
            tenant=tenant,
            slug='owner',
            defaults={'name': 'Owner'},
        )
        all_permissions = Permission.objects.all()
        RolePermission.objects.bulk_create(
            [RolePermission(role=owner_role, permission=p) for p in all_permissions],
            ignore_conflicts=True,
        )
        owner_role.membership.add(membership)

        return tenant

    @staticmethod
    def update_tenant(tenant: Tenant, **kwargs) -> Tenant:
        for k, v in kwargs.items():
            setattr(tenant, k, v)
        tenant.save()
        return tenant

    @staticmethod
    def deactivate_tenant(tenant: Tenant):
        tenant.status = 'deactivated'
        tenant.save()
