from rest_framework.permissions import BasePermission
from core.middleware.tenant import get_current_tenant
from apps.saas.models import Membership, RolePermission


class IsTenantMember(BasePermission):
    """Permits active members of the current active tenant."""
    def has_permission(self, request, view):
        tenant = get_current_tenant()
        if not tenant:
            return False
        return Membership.objects.filter(
            tenant=tenant,
            user=request.user,
            status='active'
        ).exists()


class HasPermission(BasePermission):
    """Dynamic permission class checking role permission codenames."""
    codename = None

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        tenant = get_current_tenant()
        if not tenant:
            return False

        # Query to check if the user has a role with the required permission
        return RolePermission.objects.filter(
            role__tenant=tenant,
            role__membership__user=request.user,
            role__membership__status='active',
            permission__codename=self.codename
        ).exists()

    @classmethod
    def of(cls, codename: str):
        """Factory method to generate permission classes dynamically."""
        return type(
            f"HasPermission_{codename.replace(':', '_')}",
            (cls,),
            {'codename': codename}
        )
