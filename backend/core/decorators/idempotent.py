import functools
from django.core.cache import cache
from core.exceptions import DuplicateOperationError


def idempotent(key_param: str = 'idempotency_key'):
    """Decorator to enforce idempotency on service function level."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = kwargs.get(key_param)
            if not key:
                # If key not provided, execute without idempotency checks
                return func(*args, **kwargs)

            cache_key = f"service_idemp:{func.__name__}:{key}"

            # Fast check
            status = cache.get(f"lock:{cache_key}")
            if status == 'running':
                raise DuplicateOperationError("This operation is currently in progress")

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Acquire lock
            cache.set(f"lock:{cache_key}", 'running', 60)

            try:
                result = func(*args, **kwargs)
                # Cache results for 24h
                cache.set(cache_key, result, 86400)
                return result
            finally:
                cache.delete(f"lock:{cache_key}")

        return wrapper
    return decorator
