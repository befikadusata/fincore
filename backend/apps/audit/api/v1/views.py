from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.api.v1.serializers import AuditLogSerializer
from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditService
from core.middleware.tenant import get_current_tenant
from core.permissions import HasPermission


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [HasPermission.of('audit:read')]

    def get_queryset(self):
        tenant = get_current_tenant()
        qs = AuditLog.objects.filter(tenant=tenant)

        params = self.request.query_params
        if action_filter := params.get('action'):
            qs = qs.filter(action=action_filter)
        if entity_type := params.get('entity_type'):
            qs = qs.filter(entity_type=entity_type)
        if entity_id := params.get('entity_id'):
            qs = qs.filter(entity_id=entity_id)
        if actor_id := params.get('actor_id'):
            qs = qs.filter(actor_id=actor_id)
        if date_from := params.get('date_from'):
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to := params.get('date_to'):
            qs = qs.filter(created_at__date__lte=date_to)

        return qs

    @action(detail=False, methods=['get'], url_path='entity-history')
    def entity_history(self, request):
        entity_type = request.query_params.get('entity_type')
        entity_id = request.query_params.get('entity_id')
        if not entity_type or not entity_id:
            return Response(
                {'error': 'entity_type and entity_id are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tenant = get_current_tenant()
        qs = AuditService.get_entity_history(entity_type, entity_id, tenant=tenant)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
