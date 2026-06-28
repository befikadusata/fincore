from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet, MembershipViewSet, RoleViewSet, AuthViewSet, PermissionViewSet

app_name = 'saas'

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'members', MembershipViewSet, basename='member')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', AuthViewSet.as_view({'post': 'register'}), name='register'),
    path('auth/logout/', AuthViewSet.as_view({'post': 'logout'}), name='logout'),
    path('auth/me/', AuthViewSet.as_view({'get': 'me', 'patch': 'me'}), name='me'),
]
