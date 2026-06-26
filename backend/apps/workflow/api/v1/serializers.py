from rest_framework import serializers

from apps.workflow.models import WorkflowDefinition, WorkflowInstance, WorkflowStep


class WorkflowDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowDefinition
        fields = [
            'id', 'name', 'trigger_event', 'config', 'version',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class WorkflowStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStep
        fields = [
            'id', 'step_order', 'name', 'step_type', 'status',
            'assignee', 'assignee_role', 'actor', 'action_taken',
            'comments', 'started_at', 'completed_at', 'config',
        ]
        read_only_fields = fields


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)
    definition_name = serializers.CharField(source='definition.name', read_only=True)

    class Meta:
        model = WorkflowInstance
        fields = [
            'id', 'definition', 'definition_name', 'entity_type', 'entity_id',
            'status', 'context', 'completed_at', 'steps', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class StepActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject', 'return'])
    comments = serializers.CharField(required=False, allow_blank=True, default='')
