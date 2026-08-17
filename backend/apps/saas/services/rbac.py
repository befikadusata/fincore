from django.db.models import Q
from apps.audit.constants import AuditAction
from apps.saas.models import Role, Permission, RolePermission, User, Tenant, Membership
from core.decorators.audit import auditable
from core.exceptions import MembershipNotFoundError


class RBACService:
    @staticmethod
    # Audits the returned Membership, not the User in args[0]: the membership is
    # the thing that changed, and it carries no encrypted fields.
    @auditable('membership', action=AuditAction.ROLE_ASSIGNED, target='result')
    def assign_role(user: User, tenant: Tenant, role: Role):
        membership = Membership.objects.filter(
            user=user, tenant=tenant, status='active'
        ).first()
        if not membership:
            raise MembershipNotFoundError()
        role.membership.add(membership)
        return membership

    @staticmethod
    @auditable('membership', action=AuditAction.ROLE_REMOVED, target='result')
    def remove_role(user: User, tenant: Tenant, role: Role):
        membership = Membership.objects.filter(
            user=user, tenant=tenant, status='active'
        ).first()
        if membership:
            role.membership.remove(membership)
        # Returned so the audit entry can identify the affected membership.
        return membership

    @staticmethod
    def check_permission(user: User, tenant: Tenant, permission_codename: str) -> bool:
        return RolePermission.objects.filter(
            role__membership__user=user,
            role__membership__tenant=tenant,
            role__membership__status='active',
            permission__codename=permission_codename
        ).exists()
