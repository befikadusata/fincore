from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "base-uri 'self';"
)


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        csp = getattr(settings, 'CONTENT_SECURITY_POLICY', _DEFAULT_CSP)
        response['Content-Security-Policy'] = csp
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
