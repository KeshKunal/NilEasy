from typing import Optional, Any

class NilEasyError(Exception):
    """
    Base exception for NilEasy application.
    """
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: Optional[Any] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

class ResourceNotFoundError(NilEasyError):
    """
    Raised when a requested resource is not found.
    """
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(message, code="NOT_FOUND", status_code=404, details=details)

class AuthenticationError(NilEasyError):
    """
    Raised when authentication fails.
    """
    def __init__(self, message: str = "Authentication failed", details: Optional[Any] = None):
        super().__init__(message, code="AUTHENTICATION_FAILED", status_code=401, details=details)

class ValidationError(NilEasyError):
    """
    Raised when input validation fails.
    """
    def __init__(self, message: str = "Validation error", details: Optional[Any] = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=422, details=details)

class ExternalServiceError(NilEasyError):
    """
    Raised when an external service (e.g., GST, AiSensy) fails.
    """
    def __init__(self, message: str = "External service error", details: Optional[Any] = None):
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR", status_code=502, details=details)
