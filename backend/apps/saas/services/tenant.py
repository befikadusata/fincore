from apps.saas.models import Tenant, Membership
from core.middleware.tenant import set_current_tenant
from django.db import transaction

class TenantService:
    @staticmethod
    @transaction.atomic
    def create_tenant(name: str, slug: str, owner_user) -> Tenant:
        tenant = Tenant.objects.create(name=name, slug=slug)
        # The owner becomes an active member
        Membership.objects.create(
            user=owner_user,
            tenant=tenant,
            status='active'
        )
        # TODO: Assign owner role using RBACService
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
