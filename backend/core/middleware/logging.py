import logging
import time

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('fincore.requests')

_SENSITIVE_PATHS = ('/auth/token/', '/auth/register/')


class RequestLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._log_start_time = time.monotonic()

    def process_response(self, request, response):
        duration_ms = round((time.monotonic() - getattr(request, '_log_start_time', time.monotonic())) * 1000)
        user_id = str(request.user.pk) if hasattr(request, 'user') and request.user.is_authenticated else None
        tenant_id = str(request.tenant.pk) if hasattr(request, 'tenant') and request.tenant else None

        logger.info(
            '%s %s %s %dms user=%s tenant=%s',
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            user_id,
            tenant_id,
        )
        return response
