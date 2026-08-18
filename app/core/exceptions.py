from typing import Any, Dict, Optional

from fastapi import status


class AppException(Exception):
    """Base application exception with standardized code and HTTP status."""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class BadRequestException(AppException):
    def __init__(self, message: str = "Invalid request payload.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="BAD_REQUEST",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ConflictException(AppException):
    def __init__(self, message: str = "Resource conflict.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RESOURCE_CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class AuthenticationException(AppException):
    def __init__(self, message: str = "Invalid credentials or unauthenticated request.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class MFARequiredException(AppException):
    def __init__(self, temp_token: str, message: str = "Multi-factor authentication required."):
        super().__init__(
            code="MFA_REQUIRED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"temp_token": temp_token}
        )


class AccountLockedException(AppException):
    def __init__(self, unlock_time: Optional[str] = None):
        super().__init__(
            code="ACCOUNT_LOCKED",
            message="Account has been temporarily locked due to multiple failed login attempts.",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"unlock_time": unlock_time} if unlock_time else {}
        )


class PermissionDeniedException(AppException):
    def __init__(self, permission: Optional[str] = None, message: str = "You do not have permission to perform this action."):
        super().__init__(
            code="PERMISSION_DENIED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details={"required_permission": permission} if permission else {}
        )


class ResourceNotFoundException(AppException):
    def __init__(self, resource_type: str = "Resource", resource_id: Any = None, message: Optional[str] = None):
        msg = message or f"{resource_type} with ID '{resource_id}' was not found."
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=msg,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": str(resource_id) if resource_id else None}
        )


class DuplicateResourceException(AppException):
    def __init__(self, resource_type: str, field_name: str, value: Any):
        super().__init__(
            code="DUPLICATE_RESOURCE",
            message=f"{resource_type} with {field_name} '{value}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
            details={"resource_type": resource_type, "field": field_name, "value": str(value)}
        )


class InvalidStateTransitionException(AppException):
    def __init__(self, current_status: str, target_status: str, entity_name: str = "Entity"):
        super().__init__(
            code="INVALID_STATE_TRANSITION",
            message=f"Cannot transition {entity_name} from status '{current_status}' to '{target_status}'.",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details={"current_status": current_status, "target_status": target_status, "entity": entity_name}
        )


class DoubleVotingException(AppException):
    def __init__(self, voter_id: str, message: str = "Double voting prevented. Voter has already cast a ballot."):
        super().__init__(
            code="DOUBLE_VOTING_PREVENTED",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details={"voter_id": voter_id}
        )


class VoterEligibilityException(AppException):
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="VOTER_INELIGIBLE",
            message=f"Voter is not eligible: {reason}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {}
        )


class ElectionNotActiveException(AppException):
    def __init__(self, election_id: str, current_status: str):
        super().__init__(
            code="ELECTION_NOT_ACTIVE",
            message=f"Election '{election_id}' is not currently active for voting (Status: {current_status}).",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"election_id": election_id, "status": current_status}
        )


class WebhookVerificationException(AppException):
    def __init__(self, provider: str, message: str = "Webhook signature verification failed."):
        super().__init__(
            code="WEBHOOK_VERIFICATION_FAILED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"provider": provider}
        )


class RateLimitExceededException(AppException):
    def __init__(self, retry_after_seconds: int = 60):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests. Please slow down and try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after_seconds}
        )


# Aliases for cross-compatibility
NotFoundException = ResourceNotFoundException
ValidationException = BadRequestException
