from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.audit.api.v1.views import AuditLogViewSet

app_name = 'audit'

router = DefaultRouter()
router.register('logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
