from rest_framework import serializers
from apps.saas.models import Tenant, User, Membership, Role, Permission, RolePermission


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

    class Meta:
        model = Membership
        fields = ['id', 'user', 'tenant', 'status', 'created_at']


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
