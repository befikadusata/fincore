import threading
from typing import Optional
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from apps.saas.models import Tenant, Membership

_tenant_context = threading.local()


def get_current_tenant() -> Optional[Tenant]:
    return getattr(_tenant_context, 'tenant', None)


def set_current_tenant(tenant: Optional[Tenant]) -> None:
    _tenant_context.tenant = tenant


def clear_current_tenant() -> None:
    if hasattr(_tenant_context, 'tenant'):
        delattr(_tenant_context, 'tenant')


class TenantMiddleware:
    jwt_auth = JWTAuthentication()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._resolve_tenant(request)
        try:
            response = self.get_response(request)
        finally:
            clear_current_tenant()
        return response

    def _resolve_tenant(self, request):
        tenant = None
        user = None

        # 1. Try JWT authentication (runs before DRF view auth)
        try:
            auth_result = self.jwt_auth.authenticate(request)
            if auth_result:
                user, token = auth_result
                request.user = user
                tenant_id = token.get('tenant_id')
                if tenant_id:
                    try:
                        tenant = Tenant.objects.get(id=tenant_id)
                    except (Tenant.DoesNotExist, ValueError):
                        pass
        except (InvalidToken, AuthenticationFailed):
            pass

        # 2. Fallback to X-Tenant-ID header
        if not tenant:
            tenant_id = request.headers.get('X-Tenant-ID')
            if tenant_id:
                try:
                    tenant = Tenant.objects.get(id=tenant_id)
                except (Tenant.DoesNotExist, ValueError):
                    pass

        # 3. Fallback to request.user (set by force_authenticate or session)
        current_user = user or (request.user if request.user.is_authenticated else None)
        if not tenant and current_user:
            membership = Membership.objects.filter(user=current_user, status='active').first()
            if membership:
                tenant = membership.tenant

        if tenant:
            set_current_tenant(tenant)
            request.tenant = tenant
