from django.db import models


class AuditAction(models.TextChoices):
    CREATE = 'create', 'Create'
    UPDATE = 'update', 'Update'
    DELETE = 'delete', 'Delete'
    STATUS_CHANGE = 'status_change', 'Status Change'
    LOGIN = 'login', 'Login'
    LOGOUT = 'logout', 'Logout'


class ActorType(models.TextChoices):
    USER = 'user', 'User'
    SYSTEM = 'system', 'System'
    CELERY = 'celery', 'Celery'
