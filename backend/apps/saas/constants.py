from django.db import models


class TenantStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    SUSPENDED = 'suspended', 'Suspended'
    DEACTIVATED = 'deactivated', 'Deactivated'


class MembershipStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INVITED = 'invited', 'Invited'
    SUSPENDED = 'suspended', 'Suspended'
    REMOVED = 'removed', 'Removed'
