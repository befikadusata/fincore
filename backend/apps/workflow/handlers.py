import logging

logger = logging.getLogger(__name__)


def handle_loan_submitted(event):
    """
    Instantiate the tenant's active loan-approval workflow whenever a loan is submitted.
    No-op when no active WorkflowDefinition with trigger_event='loan.submitted' exists.
    """
    from apps.workflow.constants import WorkflowStatus
    from apps.workflow.models import WorkflowDefinition, WorkflowInstance
    from apps.workflow.services.workflow_service import WorkflowService

    definition = (
        WorkflowDefinition.objects_unscoped
        .filter(tenant_id=event.tenant_id, trigger_event='loan.submitted', is_active=True)
        .order_by('-version')
        .first()
    )
    if definition is None:
        return

    # One live workflow per loan. Dispatch is at-least-once — a retry, or a
    # message replayed after the worker was down, delivers the same event again
    # — and without this each delivery built another instance, leaving the
    # approver with duplicate tasks for a decision they had already made.
    # Matched case-insensitively because the seed script writes 'loan'.
    already_running = WorkflowInstance.objects_unscoped.filter(
        tenant_id=event.tenant_id,
        entity_type__iexact='Loan',
        entity_id=str(event.entity_id),
    ).exclude(
        status__in=(WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED),
    ).exists()
    if already_running:
        logger.info('Workflow already running for loan %s; skipping', event.entity_id)
        return

    WorkflowService.instantiate(
        definition=definition,
        entity_type='Loan',
        entity_id=event.entity_id,
        context={
            'loan_id': event.entity_id,
            **event.payload,
            # The payload carries principal_amount as a string, because that is
            # how a Decimal survives JSON. Step conditions compare it against a
            # number, and `'120000.00' >= 50000` raises TypeError, which
            # evaluate_conditions swallows as "condition not met" — so every
            # amount-gated step was being skipped instead of applied.
            **_numeric(event.payload, 'principal_amount'),
        },
        tenant=event.tenant,
    )


def _numeric(payload, field):
    """{field: float} when the payload holds a numeric string, else {}."""
    try:
        return {field: float(payload[field])}
    except (KeyError, TypeError, ValueError):
        return {}


def handle_workflow_completed(event):
    """
    When a workflow over a Loan entity finishes, drive the loan to APPROVED or REJECTED.
    Only acts on workflows whose definition was triggered by 'loan.submitted'.
    """
    if event.entity_type != 'Loan':
        return

    payload = event.payload or {}
    outcome = payload.get('outcome')
    definition_id = payload.get('definition_id')

    if not definition_id:
        return

    from apps.workflow.models import WorkflowDefinition
    try:
        definition = WorkflowDefinition.objects_unscoped.get(id=definition_id)
    except WorkflowDefinition.DoesNotExist:
        return

    if definition.trigger_event != 'loan.submitted':
        return

    from django.core.exceptions import ValidationError
    from apps.finance.models.loan import Loan
    from apps.finance.services.loan_service import LoanService

    try:
        loan = Loan.objects_unscoped.get(id=event.entity_id)
    except (Loan.DoesNotExist, ValidationError, ValueError):
        return

    if outcome == 'completed':
        LoanService.approve_loan(loan, approver=None)
    elif outcome == 'rejected':
        LoanService.reject_loan(loan)
