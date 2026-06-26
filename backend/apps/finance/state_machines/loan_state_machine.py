from apps.finance.constants import LoanStatus
from core.utils.state_machine import StateMachine

LOAN_TRANSITIONS = {
    LoanStatus.CREATED: [LoanStatus.SUBMITTED],
    LoanStatus.SUBMITTED: [LoanStatus.UNDER_REVIEW, LoanStatus.REJECTED],
    LoanStatus.UNDER_REVIEW: [LoanStatus.APPROVED, LoanStatus.REJECTED],
    LoanStatus.APPROVED: [LoanStatus.DISBURSED],
    LoanStatus.DISBURSED: [LoanStatus.ACTIVE],
    LoanStatus.ACTIVE: [LoanStatus.COMPLETED, LoanStatus.DEFAULTED],
    LoanStatus.COMPLETED: [],
    LoanStatus.REJECTED: [],
    LoanStatus.DEFAULTED: [],
    LoanStatus.RETURNED: [],
}

loan_state_machine = StateMachine(LOAN_TRANSITIONS)
