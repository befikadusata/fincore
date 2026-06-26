import functools
from django.db import models as django_models
from django.forms.models import model_to_dict
from core.middleware.audit import get_audit_context


def auditable(entity_type: str, action: str = None):
    """Decorator to log mutating service operations to AuditLog.

    Scans positional args for a Django model instance (skips class/type objects).
    Captures before/after state diff when an instance is found.
    `action` defaults to 'update' when a before-state exists, 'create' otherwise.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from apps.audit.services.audit_service import AuditService
            from apps.audit.constants import AuditAction

            instance = None
            before_state = None
            for arg in args:
                if isinstance(arg, django_models.Model):
                    instance = arg
                    try:
                        before_state = model_to_dict(instance)
                    except Exception:
                        pass
                    break

            result = func(*args, **kwargs)

            after_state = None
            if instance is not None:
                try:
                    instance.refresh_from_db()
                    after_state = model_to_dict(instance)
                except Exception:
                    after_state = model_to_dict(instance)

            changes = {}
            if before_state and after_state:
                for k, v in after_state.items():
                    if before_state.get(k) != v:
                        changes[k] = {'old': str(before_state.get(k)), 'new': str(v)}

            resolved_action = action or (AuditAction.UPDATE if before_state else AuditAction.CREATE)
            entity_obj = instance if instance is not None else result
            entity_id = getattr(entity_obj, 'id', None) if entity_obj is not None else None

            AuditService.log(
                action=resolved_action,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes,
            )

            return result
        return wrapper
    return decorator
