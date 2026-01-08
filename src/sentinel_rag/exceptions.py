from typing import Any, Dict, Optional


#       BASE EXCEPTIONS
# ------------------------------


class SentinelError(Exception):
    """
    Base exception for all Sentinel RAG errors.
    """

    def __init__(
        self,
        message: str,
        code: str = "SENTINEL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


#       USER EXCEPTIONS
# ------------------------------


class UserNotFoundError(SentinelError):
    """Raised when a user is not found."""

    def __init__(self, message: str = "User not found", **kwargs):
        super().__init__(
            message=message,
            code="USER_NOT_FOUND",
            status_code=404,
            **kwargs,
        )


class UserAuthenticationError(SentinelError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            status_code=401,
            **kwargs,
        )


class UserAuthorizationError(SentinelError):
    """Raised when user lacks permissions."""

    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(
            message=message,
            code="AUTHORIZATION_FAILED",
            status_code=403,
            **kwargs,
        )


#       DOCUMENT EXCEPTIONS
# ---------------------------------


class DocumentNotFoundError(SentinelError):
    """Raised when a document is not found."""

    def __init__(self, message: str = "Document not found", **kwargs):
        super().__init__(
            message=message,
            code="DOCUMENT_NOT_FOUND",
            status_code=404,
            **kwargs,
        )


class DocumentProcessingError(SentinelError):
    """Raised when document processing fails."""

    def __init__(self, message: str = "Document processing failed", **kwargs):
        super().__init__(
            message=message,
            code="DOCUMENT_PROCESSING_ERROR",
            status_code=500,
            **kwargs,
        )


class DocumentAccessDeniedError(SentinelError):
    """Raised when user cannot access a document."""

    def __init__(self, message: str = "Access to document denied", **kwargs):
        super().__init__(
            message=message,
            code="DOCUMENT_ACCESS_DENIED",
            status_code=403,
            **kwargs,
        )


#       DEPARTMENT EXCEPTIONS
# -----------------------------------


class DepartmentNotFoundError(SentinelError):
    """Raised when a department is not found."""

    def __init__(self, message: str = "Department not found", **kwargs):
        super().__init__(
            message=message,
            code="DEPARTMENT_NOT_FOUND",
            status_code=404,
            **kwargs,
        )


#       QUERY EXCEPTIONS
# ---------------------------------


class QueryProcessingError(SentinelError):
    """Raised when query processing fails."""

    def __init__(self, message: str = "Query processing failed", **kwargs):
        super().__init__(
            message=message,
            code="QUERY_PROCESSING_ERROR",
            status_code=500,
            **kwargs,
        )


class QueryValidationError(SentinelError):
    """Raised when query validation fails."""

    def __init__(self, message: str = "Invalid query", **kwargs):
        super().__init__(
            message=message,
            code="QUERY_VALIDATION_ERROR",
            status_code=400,
            **kwargs,
        )


#       DATABASE EXCEPTIONS
# ----------------------------------


class DatabaseConnectionError(SentinelError):
    """Raised when database connection fails."""

    def __init__(self, message: str = "Database connection failed", **kwargs):
        super().__init__(
            message=message,
            code="DATABASE_CONNECTION_ERROR",
            status_code=503,
            **kwargs,
        )


class DatabaseQueryError(SentinelError):
    """Raised when a database query fails."""

    def __init__(self, message: str = "Database query failed", **kwargs):
        super().__init__(
            message=message,
            code="DATABASE_QUERY_ERROR",
            status_code=500,
            **kwargs,
        )


#       CONFIGURATION EXCEPTIONS
# -------------------------------------


class ConfigurationError(SentinelError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str = "Invalid configuration", **kwargs):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=500,
            **kwargs,
        )
