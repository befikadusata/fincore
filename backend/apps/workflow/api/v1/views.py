from django.db import models as db_models
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.workflow.api.v1.serializers import (
    StepActionSerializer,
    WorkflowDefinitionSerializer,
    WorkflowInstanceSerializer,
    WorkflowStepSerializer,
)
from apps.workflow.constants import StepStatus
from apps.workflow.models import WorkflowDefinition, WorkflowInstance, WorkflowStep
from apps.workflow.services.workflow_engine import WorkflowEngine
from apps.workflow.services.workflow_service import WorkflowService
from core.permissions import HasPermission, IsTenantMember


class WorkflowDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowDefinitionSerializer
    permission_classes = [HasPermission.of('workflow:manage')]

    def get_queryset(self):
        return WorkflowDefinition.objects.all()

    def perform_create(self, serializer):
        from core.middleware.tenant import get_current_tenant
        tenant = get_current_tenant()
        data = serializer.validated_data
        definition = WorkflowService.create_definition(
            name=data['name'],
            trigger_event=data.get('trigger_event', ''),
            config=data['config'],
            tenant=tenant,
        )
        serializer.instance = definition


class WorkflowInstanceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = WorkflowInstanceSerializer
    permission_classes = [HasPermission.of('workflow:read')]

    def get_queryset(self):
        qs = WorkflowInstance.objects.select_related('definition').prefetch_related('steps')
        entity_type = self.request.query_params.get('entity_type')
        entity_id = self.request.query_params.get('entity_id')
        status = self.request.query_params.get('status')
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if status:
            qs = qs.filter(status=status)
        return qs


class MyTasksViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Pending workflow steps assigned to the current user (by user or by role)."""
    serializer_class = WorkflowStepSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        user = self.request.user
        from apps.saas.models import Membership, Role
        from core.middleware.tenant import get_current_tenant
        tenant = get_current_tenant()

        user_roles = Role.objects_unscoped.filter(
            tenant=tenant,
            membership__user=user,
            membership__status='active',
        )

        return WorkflowStep.objects.filter(
            status=StepStatus.IN_PROGRESS,
        ).filter(
            db_models.Q(assignee=user) | db_models.Q(assignee_role__in=user_roles)
        ).select_related('instance', 'instance__definition')


class WorkflowStepViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = WorkflowStepSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return WorkflowStep.objects.all()

    @action(detail=True, methods=['post'], url_path='action')
    def take_action(self, request, pk=None):
        step = self.get_object()
        serializer = StepActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = WorkflowEngine.execute_step(
            step=step,
            action=serializer.validated_data['action'],
            actor=request.user,
            comments=serializer.validated_data.get('comments', ''),
        )
        return Response(WorkflowStepSerializer(updated).data)
