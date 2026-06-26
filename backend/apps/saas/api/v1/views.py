from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from apps.saas.models import Tenant, User, Membership, Role, Permission, RolePermission
from apps.saas.api.v1.serializers import (
    TenantSerializer, UserSerializer, MembershipSerializer,
    RoleSerializer, PermissionSerializer, SwitchTenantSerializer,
    AssignPermissionsSerializer,
)
from apps.saas.services.tenant import TenantService
from apps.saas.services.membership import MembershipService
from apps.saas.services.rbac import RBACService
from core.permissions import IsTenantMember, HasPermission


class TenantViewSet(viewsets.ModelViewSet):
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Tenant.objects.filter(memberships__user=self.request.user)

    def perform_create(self, serializer):
        tenant = TenantService.create_tenant(
            name=serializer.validated_data['name'],
            slug=serializer.validated_data['slug'],
            owner_user=self.request.user,
        )
        serializer.instance = tenant

    @action(detail=False, methods=['post'])
    def switch(self, request):
        serializer = SwitchTenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant_id = serializer.validated_data['tenant_id']

        membership = Membership.objects.filter(
            user=request.user, tenant_id=tenant_id, status='active'
        ).first()
        if not membership:
            return Response(
                {"error": "Not a member of this tenant"},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(request.user)
        refresh['tenant_id'] = str(tenant_id)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class MembershipViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Membership.objects.none()
        return Membership.objects.filter(tenant=tenant)

    @action(detail=False, methods=['post'])
    def invite(self, request):
        email = request.data.get('email')
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {"error": "No tenant context"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership = MembershipService.invite_member(tenant, email)
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def remove(self, request, pk=None):
        membership = self.get_object()
        MembershipService.remove_member(membership.tenant, membership.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleViewSet(viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Role.objects.none()
        return Role.objects.filter(tenant=tenant)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated, IsTenantMember, HasPermission.of('roles:assign_permissions')],
    )
    def assign_permissions(self, request, pk=None):
        role = self.get_object()
        serializer = AssignPermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for perm_id in serializer.validated_data['permission_ids']:
            RolePermission.objects.get_or_create(
                role=role,
                permission_id=perm_id,
            )

        return Response(RoleSerializer(role).data)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated, IsTenantMember, HasPermission.of('roles:assign_members')],
    )
    def assign_members(self, request, pk=None):
        role = self.get_object()
        user_ids = request.data.get('user_ids', [])
        for uid in user_ids:
            membership = Membership.objects.filter(
                user_id=uid, tenant=role.tenant, status='active'
            ).first()
            if membership:
                membership.roles.add(role)

        return Response(RoleSerializer(role).data)


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "User already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.create_user(
            email=email, password=password,
            first_name=first_name, last_name=last_name,
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get', 'patch'],
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        if request.method == 'GET':
            tenants = Tenant.objects.filter(memberships__user=request.user)
            return Response({
                'user': UserSerializer(request.user).data,
                'tenants': TenantSerializer(tenants, many=True).data,
            })

        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)
