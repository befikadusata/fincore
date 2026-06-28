from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers as drf_serializers
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from apps.saas.models import Tenant, User, Membership, Role, Permission, RolePermission, Plan
from apps.saas.api.v1.serializers import (
    TenantSerializer, UserSerializer, MembershipSerializer,
    RoleSerializer, PermissionSerializer, SwitchTenantSerializer,
    AssignPermissionsSerializer, RegisterSerializer, PlanSerializer,
)
from apps.saas.services.tenant import TenantService
from apps.saas.services.membership import MembershipService
from apps.saas.services.rbac import RBACService
from core.permissions import IsTenantMember, HasPermission
from core.throttles import AuthAnonThrottle


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


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]
    queryset = Permission.objects.all()
    pagination_class = None


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Plan.objects_unscoped.filter(is_active=True).prefetch_related('features')


class MembershipViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Membership.objects.none()
        return (
            Membership.objects.filter(tenant=tenant)
            .select_related('user')
            .prefetch_related('roles')
        )

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
        return Role.objects.filter(tenant=tenant).prefetch_related('role_permissions__permission')

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tenant context")
        serializer.save(tenant=tenant)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated, IsTenantMember],
    )
    def assign_permissions(self, request, pk=None):
        role = self.get_object()
        serializer = AssignPermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Replace: clear existing, add new
        RolePermission.objects.filter(role=role).delete()
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

    def get_permissions(self):
        if self.action in ('logout', 'me'):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(detail=False, methods=['post'], throttle_classes=[AuthAnonThrottle])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            validate_password(data['password'])
        except DjangoValidationError as exc:
            raise drf_serializers.ValidationError({'password': list(exc.messages)})

        if User.objects.filter(email=data['email']).exists():
            return Response(
                {"error": "User already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {'error': 'Invalid or already invalidated token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

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
