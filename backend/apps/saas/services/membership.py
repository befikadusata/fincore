from apps.audit.constants import AuditAction
from apps.saas.models import Membership, User, Tenant
from core.decorators.audit import auditable

class MembershipService:
    @staticmethod
    @auditable('membership', action=AuditAction.CREATE, target='result')
    def invite_member(tenant: Tenant, email: str) -> Membership:
        email = User.objects.normalize_email(email)
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(email=email, password=None)
        membership, created = Membership.objects.get_or_create(
            user=user,
            tenant=tenant,
            defaults={'status': 'invited'}
        )
        return membership

    @staticmethod
    @auditable('membership', action=AuditAction.DELETE, target='result')
    def remove_member(tenant: Tenant, user: User):
        Membership.objects.filter(tenant=tenant, user=user).update(status='removed')
        # Returned so the audit entry can identify the affected membership.
        return Membership.objects.filter(tenant=tenant, user=user).first()
