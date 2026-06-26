from django.db import models


class WorkflowStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    FAILED = 'failed', 'Failed'


class StepType(models.TextChoices):
    APPROVAL = 'approval', 'Approval'
    ACTION = 'action', 'Action'
    NOTIFICATION = 'notification', 'Notification'
    CONDITION = 'condition', 'Condition'


class StepStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    REJECTED = 'rejected', 'Rejected'
    SKIPPED = 'skipped', 'Skipped'
    RETURNED = 'returned', 'Returned'


class StepAction(models.TextChoices):
    APPROVE = 'approve', 'Approve'
    REJECT = 'reject', 'Reject'
    RETURN = 'return', 'Return'
