import logging

logger = logging.getLogger(__name__)


def handle_loan_submitted(event):
    """
    Instantiate the tenant's active loan-approval workflow whenever a loan is submitted.
    No-op when no active WorkflowDefinition with trigger_event='loan.submitted' exists.
    """
    from apps.workflow.models import WorkflowDefinition
    from apps.workflow.services.workflow_service import WorkflowService

    definition = (
        WorkflowDefinition.objects_unscoped
        .filter(tenant_id=event.tenant_id, trigger_event='loan.submitted', is_active=True)
        .order_by('-version')
        .first()
    )
    if definition is None:
        return

    WorkflowService.instantiate(
        definition=definition,
        entity_type='Loan',
        entity_id=event.entity_id,
        context={'loan_id': event.entity_id, **event.payload},
        tenant=event.tenant,
    )


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
