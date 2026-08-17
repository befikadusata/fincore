from django.db import models


class AuditAction(models.TextChoices):
    CREATE = 'create', 'Create'
    UPDATE = 'update', 'Update'
    DELETE = 'delete', 'Delete'
    STATUS_CHANGE = 'status_change', 'Status Change'
    LOGIN = 'login', 'Login'
    LOGOUT = 'logout', 'Logout'

    # Loan lifecycle. Recording these as 'status_change' would technically be
    # true but useless to an auditor: approving and disbursing carry very
    # different accountability, so each transition gets its own verb.
    SUBMITTED = 'submitted', 'Submitted'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    DISBURSED = 'disbursed', 'Disbursed'
    REPAID = 'repaid', 'Repaid'
    DEFAULTED = 'defaulted', 'Defaulted'

    # Money movement.
    CREDIT = 'credit', 'Credit'
    DEBIT = 'debit', 'Debit'

    # Access control and billing.
    ROLE_ASSIGNED = 'role_assigned', 'Role Assigned'
    ROLE_REMOVED = 'role_removed', 'Role Removed'
    SUBSCRIBED = 'subscribed', 'Subscribed'
    CANCELLED = 'cancelled', 'Cancelled'


class ActorType(models.TextChoices):
    USER = 'user', 'User'
    SYSTEM = 'system', 'System'
    CELERY = 'celery', 'Celery'
