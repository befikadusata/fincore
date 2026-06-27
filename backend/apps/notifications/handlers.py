import logging

logger = logging.getLogger(__name__)


def _notify(user, tenant, event_type, title, body, entity_type='', entity_id=''):
    try:
        from apps.notifications.services.notification_service import NotificationService
        NotificationService.notify(
            user=user,
            tenant=tenant,
            event_type=event_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=str(entity_id),
        )
    except Exception:
        logger.exception('Notification dispatch failed for event %s', event_type)


def handle_loan_approved(event):
    from apps.finance.models.loan import Loan
    try:
        loan = Loan.objects_unscoped.select_related('borrower').get(id=event.entity_id)
    except (Loan.DoesNotExist, Exception):
        return
    _notify(
        user=loan.borrower,
        tenant=event.tenant,
        event_type=event.event_type,
        title='Loan Approved',
        body=f'Your loan of {loan.principal_amount} has been approved.',
        entity_type='Loan',
        entity_id=loan.id,
    )


def handle_loan_disbursed(event):
    from apps.finance.models.loan import Loan
    try:
        loan = Loan.objects_unscoped.select_related('borrower').get(id=event.entity_id)
    except (Loan.DoesNotExist, Exception):
        return
    _notify(
        user=loan.borrower,
        tenant=event.tenant,
        event_type=event.event_type,
        title='Loan Disbursed',
        body=f'Your loan of {loan.principal_amount} has been disbursed to your wallet.',
        entity_type='Loan',
        entity_id=loan.id,
    )


def handle_repayment_due_soon(event):
    """Notify borrower about an upcoming installment due in 3 days."""
    from apps.finance.models.loan import Loan
    payload = event.payload or {}
    loan_id = payload.get('loan_id') or event.entity_id
    due_date = payload.get('due_date', '')
    amount = payload.get('amount', '')
    try:
        loan = Loan.objects_unscoped.select_related('borrower').get(id=loan_id)
    except (Loan.DoesNotExist, Exception):
        return
    _notify(
        user=loan.borrower,
        tenant=event.tenant,
        event_type=event.event_type,
        title='Repayment Due Soon',
        body=f'A repayment of {amount} is due on {due_date}. Please ensure your wallet is funded.',
        entity_type='Loan',
        entity_id=loan.id,
    )


def handle_workflow_step_assigned(event):
    """Notify the assignee of a workflow step."""
    payload = event.payload or {}
    assignee_id = payload.get('assignee_id')
    if not assignee_id:
        return
    from apps.saas.models import User
    try:
        assignee = User.objects.get(id=assignee_id)
    except (User.DoesNotExist, Exception):
        return
    step_name = payload.get('step_name', 'a task')
    _notify(
        user=assignee,
        tenant=event.tenant,
        event_type=event.event_type,
        title='Action Required',
        body=f'You have been assigned to review: {step_name}.',
        entity_type=event.entity_type,
        entity_id=event.entity_id,
    )


def handle_subscription_payment_failed(event):
    """Notify tenant admins when a subscription payment fails."""
    from apps.saas.models import Membership
    admins = Membership.objects.filter(
        tenant=event.tenant, roles__slug='admin'
    ).select_related('user')
    for membership in admins:
        _notify(
            user=membership.user,
            tenant=event.tenant,
            event_type=event.event_type,
            title='Payment Failed',
            body='Your subscription payment has failed. Please update your payment method.',
            entity_type='Tenant',
            entity_id=str(event.tenant_id),
        )
