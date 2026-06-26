from django.db import models


class TenantManager(models.Manager):
    """Manager to enforce tenant isolation."""
    def get_queryset(self):
        from core.middleware.tenant import get_current_tenant
        tenant = get_current_tenant()
        if tenant:
            return super().get_queryset().filter(tenant=tenant)
        return super().get_queryset().none()

    def unscoped(self):
        """Bypass tenant auto-scoping."""
        return super().get_queryset()
