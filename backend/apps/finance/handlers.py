import logging

logger = logging.getLogger(__name__)


def handle_loan_approved(event):
    """Auto-disburse a loan once it reaches APPROVED status."""
    from django.core.exceptions import ValidationError
    from apps.finance.constants import LoanStatus
    from apps.finance.models.loan import Loan
    from apps.finance.services.loan_service import LoanService

    try:
        loan = Loan.objects_unscoped.get(id=event.entity_id)
    except (Loan.DoesNotExist, ValidationError, ValueError):
        return

    if loan.status != LoanStatus.APPROVED:
        return

    LoanService.disburse_loan(loan)
