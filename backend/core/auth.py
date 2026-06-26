from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.saas.models import Membership
from apps.saas.models import User


class FinCoreTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        membership = Membership.objects.filter(
            user=user, status='active'
        ).select_related('tenant').first()
        if membership:
            token['tenant_id'] = str(membership.tenant_id)
        return token
