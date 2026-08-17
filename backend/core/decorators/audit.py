import functools

from django.db import models as django_models
from django.forms.models import model_to_dict

from core.fields import EncryptedCharField
from core.middleware.audit import get_audit_context

REDACTED = '[redacted]'


def _capture_state(instance):
    return model_to_dict(instance)


def _encrypted_field_names(instance):
    """Names of fields whose values must never reach AuditLog.changes.

    AuditLog.changes is a plain JSONField, but model_to_dict returns the
    *decrypted* value of an EncryptedCharField — so diffing a model that has one
    (User.first_name / last_name) would copy plaintext PII out of the encrypted
    column into an unencrypted one. Detect by field type rather than by name so
    this keeps holding for fields added later.
    """
    return {
        field.name
        for field in instance._meta.get_fields()
        if isinstance(field, EncryptedCharField)
    }


def _diff(before, after, protected):
    """Field-level diff, with protected fields reported as changed but redacted.

    Dropping protected fields entirely would be safe but would hide the fact
    that someone edited them, which is exactly what an audit log exists to show.
    """
    changes = {}
    for key, new_value in after.items():
        old_value = before.get(key)
        if old_value == new_value:
            continue
        if key in protected:
            changes[key] = {'old': REDACTED, 'new': REDACTED}
        else:
            changes[key] = {'old': str(old_value), 'new': str(new_value)}
    return changes


def _resolve_actor_type():
    """Classify who is acting: a request user, a Celery worker, or the system.

    AuditService defaults to ActorType.USER, which is wrong for the scheduled
    jobs that mutate loans and subscriptions without any request context.
    """
    from apps.audit.constants import ActorType

    if get_audit_context().get('user_id'):
        return ActorType.USER

    try:
        from celery import current_task

        if current_task is not None and getattr(current_task, 'request', None) is not None:
            if current_task.request.id is not None:
                return ActorType.CELERY
    except Exception:
        pass

    return ActorType.SYSTEM


def _resolve_tenant(*candidates):
    """Find the tenant an audit entry belongs to.

    AuditLogViewSet filters on tenant, so an entry written with tenant=None is
    invisible through the API. Prefer the audited row's own tenant — it is set
    even in Celery, where no request-scoped tenant exists — and fall back to
    the tenant middleware.
    """
    from apps.saas.models import Tenant

    for obj in candidates:
        if not isinstance(obj, django_models.Model):
            continue
        if isinstance(obj, Tenant):
            return obj
        tenant = getattr(obj, 'tenant', None)
        if tenant is not None:
            return tenant

    from core.middleware.tenant import get_current_tenant

    return get_current_tenant()


def auditable(entity_type: str, action: str = None, target: str = 'auto'):
    """Decorator to log mutating service operations to AuditLog.

    `target='auto'` scans positional args for a Django model instance (skipping
    class/type objects) and captures a before/after state diff. `target='result'`
    audits the value the function returns instead, for create-style services
    whose new row does not exist yet when the call begins.

    `action` defaults to 'update' when a before-state exists, 'create' otherwise.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from apps.audit.services.audit_service import AuditService
            from apps.audit.constants import AuditAction

            instance = None
            before_state = None
            if target != 'result':
                # Positional args win, then keyword args — services are called
                # both ways, and a keyword-only call site should still produce a
                # before/after diff rather than an empty `changes`.
                for arg in (*args, *kwargs.values()):
                    if isinstance(arg, django_models.Model):
                        instance = arg
                        try:
                            before_state = _capture_state(instance)
                        except Exception:
                            pass
                        break

            result = func(*args, **kwargs)

            after_state = None
            if instance is not None:
                try:
                    instance.refresh_from_db()
                    after_state = _capture_state(instance)
                except Exception:
                    after_state = _capture_state(instance)

            changes = {}
            if before_state and after_state:
                changes = _diff(before_state, after_state, _encrypted_field_names(instance))

            resolved_action = action or (AuditAction.UPDATE if before_state else AuditAction.CREATE)
            entity_obj = instance if instance is not None else result
            entity_id = getattr(entity_obj, 'id', None) if entity_obj is not None else None

            AuditService.log(
                action=resolved_action,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes,
                actor_type=_resolve_actor_type(),
                tenant=_resolve_tenant(entity_obj, *args),
            )

            return result
        return wrapper
    return decorator
