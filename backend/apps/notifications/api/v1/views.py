from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsTenantMember
from core.middleware.tenant import get_current_tenant
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.api.v1.serializers import NotificationSerializer, NotificationPreferenceSerializer
from apps.notifications.services.notification_service import NotificationService


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Notification.objects_unscoped.filter(
            tenant=get_current_tenant(),
            recipient=self.request.user,
        )

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        updated = NotificationService.mark_read(notification)
        return Response(NotificationSerializer(updated).data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        count = NotificationService.mark_all_read(request.user, get_current_tenant())
        return Response({'marked_read': count})


class NotificationPreferenceViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return NotificationPreference.objects_unscoped.filter(
            tenant=get_current_tenant(),
            user=self.request.user,
        )

    def perform_create(self, serializer):
        tenant = get_current_tenant()
        serializer.save(tenant=tenant, user=self.request.user)
