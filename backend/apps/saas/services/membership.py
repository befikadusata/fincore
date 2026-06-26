from apps.saas.models import Membership, User, Tenant

class MembershipService:
    @staticmethod
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
    def remove_member(tenant: Tenant, user: User):
        Membership.objects.filter(tenant=tenant, user=user).update(status='removed')
