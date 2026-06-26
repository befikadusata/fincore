import logging
from typing import Any, Dict, Optional

from apps.audit.constants import ActorType

logger = logging.getLogger(__name__)


class AuditService:
    @classmethod
    def log(
        cls,
        action: str,
        entity_type: str,
        entity_id: Optional[Any] = None,
        changes: Optional[Dict[str, Any]] = None,
        actor_id: Optional[Any] = None,
        actor_type: str = ActorType.USER,
        tenant=None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        from apps.audit.models import AuditLog
        from core.middleware.audit import get_audit_context

        ctx = get_audit_context()
        entry = AuditLog(
            tenant=tenant,
            actor_id=actor_id or ctx.get('user_id'),
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else '',
            changes=changes or {},
            ip_address=ip_address or ctx.get('ip_address'),
            user_agent=user_agent or ctx.get('user_agent') or '',
        )
        try:
            entry.save()
        except Exception:
            logger.exception(
                'Failed to write audit log for %s %s/%s', action, entity_type, entity_id
            )

    @classmethod
    def get_entity_history(cls, entity_type: str, entity_id: Any, tenant=None):
        from apps.audit.models import AuditLog

        qs = AuditLog.objects.filter(
            entity_type=entity_type,
            entity_id=str(entity_id),
        )
        if tenant is not None:
            qs = qs.filter(tenant=tenant)
        return qs.order_by('created_at')
