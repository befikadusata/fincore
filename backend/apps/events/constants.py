from django.db import models


class EventStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    PROCESSED = 'processed', 'Processed'
    FAILED = 'failed', 'Failed'
    DEAD_LETTER = 'dead_letter', 'Dead Letter'


class EventType(models.TextChoices):
    LOAN_SUBMITTED = 'loan.submitted', 'Loan Submitted'
    LOAN_APPROVED = 'loan.approved', 'Loan Approved'
    LOAN_REJECTED = 'loan.rejected', 'Loan Rejected'
    LOAN_DISBURSED = 'loan.disbursed', 'Loan Disbursed'
    LOAN_DEFAULTED = 'loan.defaulted', 'Loan Defaulted'
    LOAN_COMPLETED = 'loan.completed', 'Loan Completed'
    LOAN_OVERDUE = 'loan.overdue', 'Loan Overdue'
    REPAYMENT_RECEIVED = 'repayment.received', 'Repayment Received'
    REPAYMENT_DUE_SOON = 'repayment.due_soon', 'Repayment Due Soon'
    WORKFLOW_STEP_ASSIGNED = 'workflow.step_assigned', 'Workflow Step Assigned'
    WORKFLOW_COMPLETED = 'workflow.completed', 'Workflow Completed'
    SUBSCRIPTION_PAYMENT_FAILED = 'subscription.payment_failed', 'Subscription Payment Failed'
