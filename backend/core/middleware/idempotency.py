from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from core.models import IdempotencyRecord


class IdempotencyMiddleware(MiddlewareMixin):
    IDEMPOTENCY_TTL = timedelta(hours=24)

    def process_request(self, request):
        if request.method not in ('POST', 'PUT', 'PATCH'):
            return None

        key = request.headers.get('Idempotency-Key')
        if not key:
            return None

        user = request.user if request.user.is_authenticated else None
        user_id = user.id if user else 'anonymous'

        # Check DB first
        record = IdempotencyRecord.objects.filter(
            key=key,
            user=user,
            expires_at__gt=timezone.now()
        ).first()
        if record:
            return HttpResponse(
                content=record.response_body,
                status=record.response_status,
                content_type=record.response_content_type
            )

        # Check cache as fast layer
        cache_key = f"idemp:{user_id}:{key}"
        cached = cache.get(cache_key)
        if cached:
            return HttpResponse(
                content=cached['content'],
                status=cached['status'],
                content_type=cached['content_type']
            )

        request._idempotency_key = key
        request._idempotency_user = user
        request._idempotency_cache_key = cache_key
        return None

    def process_response(self, request, response):
        key = getattr(request, '_idempotency_key', None)
        if not key or not (200 <= response.status_code < 300):
            return response

        user = getattr(request, '_idempotency_user', None)
        cache_key = getattr(request, '_idempotency_cache_key', None)
        body = response.content.decode('utf-8')
        content_type = response.headers.get('Content-Type', 'application/json')

        # Persist in DB — get_or_create is race-safe: if a concurrent duplicate
        # request wins the insert, the unique constraint raises IntegrityError
        # and Django retries as a GET, returning the winner's stored record.
        IdempotencyRecord.objects.get_or_create(
            key=key,
            user=user,
            defaults={
                'response_status': response.status_code,
                'response_body': body,
                'response_content_type': content_type,
                'expires_at': timezone.now() + self.IDEMPOTENCY_TTL,
            },
        )

        # Cache for fast access
        cache.set(cache_key, {
            'content': body,
            'status': response.status_code,
            'content_type': content_type,
        }, int(self.IDEMPOTENCY_TTL.total_seconds()))

        return response
