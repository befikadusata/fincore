from typing import Any, Optional
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


class FinCoreError(Exception):
    """Base exception for all system/domain exceptions."""
    def __init__(self, message: str, code: str = 'fincore_error', details: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.details = details


class TenantMismatchError(FinCoreError):
    def __init__(self, message: str = "Tenant context mismatch", details: Optional[Any] = None):
        super().__init__(message, code='tenant_mismatch', details=details)


class InsufficientFundsError(FinCoreError):
    def __init__(self, message: str = "Insufficient wallet funds", details: Optional[Any] = None):
        super().__init__(message, code='insufficient_funds', details=details)


class InvalidStateTransitionError(FinCoreError):
    def __init__(self, current_state: str, attempted_state: str, details: Optional[Any] = None):
        message = f"Cannot transition from {current_state} to {attempted_state}"
        super().__init__(message, code='invalid_transition', details=details)


class DuplicateOperationError(FinCoreError):
    def __init__(self, message: str = "Duplicate operation detected", details: Optional[Any] = None):
        super().__init__(message, code='duplicate_operation', details=details)


class MembershipNotFoundError(FinCoreError):
    def __init__(self, message: str = "User has no active membership in this tenant", details: Optional[Any] = None):
        super().__init__(message, code='membership_not_found', details=details)


def fincore_exception_handler(exc: Exception, context: Any) -> Optional[Response]:
    """Custom exception handler for DRF to standardise errors."""
    response = exception_handler(exc, context)

    if isinstance(exc, FinCoreError):
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(exc, TenantMismatchError):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, (InvalidStateTransitionError, DuplicateOperationError)):
            status_code = status.HTTP_409_CONFLICT

        return Response(
            {
                'error': {
                    'code': exc.code,
                    'message': str(exc),
                    'details': exc.details
                }
            },
            status=status_code
        )

    # Wrap standard DRF errors
    if response is not None:
        response.data = {
            'error': {
                'code': 'validation_error' if response.status_code == 400 else 'api_error',
                'message': 'API Error occurred',
                'details': response.data
            }
        }

    return response
