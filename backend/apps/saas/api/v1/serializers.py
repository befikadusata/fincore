from rest_framework import serializers
from apps.saas.models import Tenant, User, Membership, Role, Permission, RolePermission, Plan, PlanFeature


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(min_length=8, max_length=128, write_only=True)
    first_name = serializers.CharField(max_length=150, default='', allow_blank=True)
    last_name = serializers.CharField(max_length=150, default='', allow_blank=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_active', 'created_at']


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'status', 'created_at']
        read_only_fields = ['status']

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Name must be at least 2 characters.')
        return value.strip()


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ['id', 'user', 'tenant', 'status', 'roles', 'created_at']

    def get_roles(self, obj):
        return [{'id': str(role.id), 'name': role.name, 'slug': role.slug} for role in obj.roles.all()]


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'description']


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'slug', 'permissions']

    def get_permissions(self, obj):
        return [
            {'id': rp.permission.id, 'codename': rp.permission.codename}
            for rp in obj.role_permissions.select_related('permission').all()
        ]


class SwitchTenantSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()


class AssignPermissionsSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(child=serializers.UUIDField())


class PlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanFeature
        fields = ['id', 'name', 'codename', 'description']


class PlanSerializer(serializers.ModelSerializer):
    features = PlanFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'slug', 'description',
            'monthly_price', 'annual_price', 'currency',
            'is_active', 'features',
        ]
