import threading
from typing import Dict, Any
from django.utils.deprecation import MiddlewareMixin

_audit_context = threading.local()


def get_audit_context() -> Dict[str, Any]:
    return getattr(_audit_context, 'context', {
        'ip_address': None,
        'user_agent': None,
        'user_id': None
    })


def set_audit_context(context: Dict[str, Any]) -> None:
    _audit_context.context = context


def clear_audit_context() -> None:
    if hasattr(_audit_context, 'context'):
        delattr(_audit_context, 'context')


class AuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        x_forwarded = request.headers.get('X-Forwarded-For')
        if x_forwarded:
            ip = x_forwarded.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        context = {
            'ip_address': ip,
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'user_id': request.user.id if request.user.is_authenticated else None
        }
        set_audit_context(context)

    def process_response(self, request, response):
        clear_audit_context()
        return response
