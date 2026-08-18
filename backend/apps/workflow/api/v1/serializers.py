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
    # The dashboard sends uppercase verbs and calls the field `comment`; older
    # API clients send lowercase and `comments`. Both are accepted rather than
    # breaking either caller.
    action = serializers.CharField()
    comments = serializers.CharField(required=False, allow_blank=True, default='')
    comment = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_action(self, value):
        normalised = value.strip().lower()
        if normalised not in ('approve', 'reject', 'return'):
            raise serializers.ValidationError(
                f"'{value}' is not a valid action. Expected approve, reject or return."
            )
        return normalised

    def validate(self, attrs):
        if not attrs.get('comments') and attrs.get('comment'):
            attrs['comments'] = attrs['comment']
        attrs.pop('comment', None)
        return attrs


class MyTaskListSerializer(serializers.ListSerializer):
    """Loads every task's loan in one query.

    WorkflowInstance points at its subject by (entity_type, entity_id) strings
    rather than a foreign key, so there is nothing to select_related and a
    per-row lookup would be N+1.
    """

    def to_representation(self, data):
        rows = list(data)
        loan_ids = [
            row.instance.entity_id
            for row in rows
            if _is_loan(row.instance) and row.instance.entity_id
        ]
        self.child.loans = _loans_by_id(loan_ids)
        return super().to_representation(rows)


def _is_loan(instance):
    """Whether a workflow instance is deciding a loan.

    The two writers disagree on case: handle_loan_submitted follows the domain
    event and stores 'Loan', while the seed script and the workflow tests store
    'loan'. An exact match here silently failed to resolve half the instances,
    and the inbox rendered those tasks with no borrower and no amount.
    """
    return (instance.entity_type or '').lower() == 'loan'


def _loans_by_id(loan_ids):
    if not loan_ids:
        return {}
    from apps.finance.models.loan import Loan

    loans = Loan.objects.filter(id__in=loan_ids).select_related('product', 'borrower')
    return {str(loan.id): loan for loan in loans}


class MyTaskSerializer(serializers.ModelSerializer):
    """A pending step, flattened together with the loan it is deciding.

    The task inbox has to show what is being approved, not just that something
    is — so the loan's borrower, amount and status are folded in here rather
    than leaving the client to fetch each loan separately.
    """
    instance_id = serializers.UUIDField(source='instance.id', read_only=True)
    entity_type = serializers.CharField(source='instance.entity_type', read_only=True)
    entity_id = serializers.CharField(source='instance.entity_id', read_only=True)
    submitted_at = serializers.DateTimeField(source='started_at', read_only=True)
    borrower_name = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    outstanding_balance = serializers.SerializerMethodField()
    loan_term_months = serializers.SerializerMethodField()
    loan_status = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowStep
        list_serializer_class = MyTaskListSerializer
        fields = [
            'id', 'instance_id', 'entity_type', 'entity_id', 'name', 'step_type',
            'status', 'submitted_at', 'borrower_name', 'product_name', 'amount',
            'outstanding_balance', 'loan_term_months', 'loan_status', 'comments',
        ]
        read_only_fields = fields

    def _loan(self, obj):
        if not _is_loan(obj.instance):
            return None
        cached = getattr(self, 'loans', None)
        if cached is not None:
            return cached.get(obj.instance.entity_id)
        from apps.finance.models.loan import Loan

        return Loan.objects.filter(id=obj.instance.entity_id).first()

    def get_borrower_name(self, obj):
        loan = self._loan(obj)
        if not loan:
            # Fall back to the snapshot the workflow captured, so a task for a
            # non-loan entity still names its subject.
            return obj.instance.context.get('borrower', '')
        name = f'{loan.borrower.first_name} {loan.borrower.last_name}'.strip()
        return name or loan.borrower.email

    def get_product_name(self, obj):
        loan = self._loan(obj)
        return loan.product.name if loan else obj.instance.context.get('product')

    def get_amount(self, obj):
        loan = self._loan(obj)
        if loan:
            return loan.principal_amount
        return obj.instance.context.get('principal_amount')

    def get_outstanding_balance(self, obj):
        loan = self._loan(obj)
        return loan.outstanding_balance if loan else None

    def get_loan_term_months(self, obj):
        loan = self._loan(obj)
        return loan.term_months if loan else obj.instance.context.get('term_months')

    def get_loan_status(self, obj):
        loan = self._loan(obj)
        return loan.status if loan else None

    def get_comments(self, obj):
        """Notes left on earlier steps of the same workflow.

        An approver deciding a step needs the trail of what previous reviewers
        said, which lives on sibling steps rather than on this one.
        """
        siblings = [
            step for step in obj.instance.steps.all()
            if step.comments and step.id != obj.id
        ]
        return [
            {
                'id': str(step.id),
                'actor_name': step.actor.email if step.actor else '',
                'action': step.action_taken or step.status,
                'comment': step.comments,
                'created_at': step.completed_at or step.started_at,
            }
            for step in siblings
        ]
