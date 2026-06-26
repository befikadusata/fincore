from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth Endpoints
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # App API routes
    path('api/v1/saas/', include('apps.saas.api.v1.urls')),
    path('api/v1/finance/', include('apps.finance.api.v1.urls')),
    path('api/v1/workflow/', include('apps.workflow.api.v1.urls')),
    path('api/v1/audit/', include('apps.audit.api.v1.urls')),
    path('api/v1/events/', include('apps.events.api.v1.urls')),
    path('api/v1/notifications/', include('apps.notifications.api.v1.urls')),
    path('api/v1/billing/', include('apps.billing.api.v1.urls')),
]
