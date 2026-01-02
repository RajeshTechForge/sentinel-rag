"""
FastAPI Middleware and Decorators for Automatic Audit Logging
"""

import time
from functools import wraps
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from .audit_service import (
    Action,
    AuditLogEntry,
    AuditService,
    EventCategory,
    EventOutcome,
    extract_client_info,
)


# ============================================
#               MIDDLEWARE
# ============================================


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log all HTTP requests.
    Useful for capturing general API access patterns.
    """

    def __init__(self, app, audit_service: AuditService):
        super().__init__(app)
        self.audit_service = audit_service

    async def dispatch(self, request: Request, call_next):
        # Skip health checks and static files
        if request.url.path in ["/health", "/metrics", "/favicon.ico"]:
            return await call_next(request)

        start_time = time.time()
        client_info = extract_client_info(request)

        # Get user from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        user_email = getattr(request.state, "user_email", None)

        try:
            response = await call_next(request)
            outcome = (
                EventOutcome.SUCCESS
                if response.status_code < 400
                else EventOutcome.FAILURE
            )
            error_msg = None
        except Exception as e:
            outcome = EventOutcome.FAILURE
            error_msg = str(e)
            raise
        finally:
            # Log the request
            duration_ms = (time.time() - start_time) * 1000

            entry = AuditLogEntry(
                user_id=user_id,
                user_email=user_email,
                session_id=client_info["session_id"],
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                event_category=EventCategory.SYSTEM,
                event_type="api_request",
                action=self._map_http_method(request.method),
                outcome=outcome,
                error_message=error_msg,
                metadata={
                    "path": request.url.path,
                    "method": request.method,
                    "duration_ms": round(duration_ms, 2),
                    "status_code": (
                        response.status_code if "response" in locals() else None
                    ),
                },
            )

            # Fire and forget (don't block response)
            try:
                await self.audit_service.log(entry)
            except Exception:
                # Log to stderr but don't fail the request
                pass

        return response

    @staticmethod
    def _map_http_method(method: str) -> Action:
        """Map HTTP methods to audit actions"""
        method_map = {
            "GET": Action.READ,
            "POST": Action.WRITE,
            "PUT": Action.UPDATE,
            "PATCH": Action.UPDATE,
            "DELETE": Action.DELETE,
        }
        return method_map.get(method, Action.EXECUTE)


# ============================================
#               DECORATORS
# ============================================


def audit_data_access(resource_type: str, include_pii: bool = False):
    """
    Decorator for auditing data access operations.

    Usage:
        @audit_data_access(resource_type="document", include_pii=True)
        async def get_document(doc_id: UUID, user: User):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract audit service and request from dependency injection
            request: Optional[Request] = kwargs.get("request")
            audit_service: Optional[AuditService] = kwargs.get("audit_service")

            if not audit_service or not request:
                # If dependencies not available, just execute function
                return await func(*args, **kwargs)

            # Get user info from request state
            user_id = getattr(request.state, "user_id", None)
            user_email = getattr(request.state, "user_email", None)
            client_info = extract_client_info(request)

            start_time = time.time()

            try:
                # Execute the function
                result = await func(*args, **kwargs)
                outcome = EventOutcome.SUCCESS
                error_msg = None

                # Extract resource info from result or kwargs
                resource_id = kwargs.get(f"{resource_type}_id")
                resource_name = (
                    getattr(result, "name", None) if hasattr(result, "name") else None
                )

                return result

            except Exception as e:
                outcome = EventOutcome.FAILURE
                error_msg = str(e)
                resource_id = kwargs.get(f"{resource_type}_id")
                resource_name = None
                raise

            finally:
                # Log the access
                duration_ms = (time.time() - start_time) * 1000

                entry = AuditLogEntry(
                    user_id=user_id,
                    user_email=user_email,
                    session_id=client_info["session_id"],
                    ip_address=client_info["ip_address"],
                    user_agent=client_info["user_agent"],
                    event_category=EventCategory.DATA_ACCESS,
                    event_type=f"{resource_type}_access",
                    action=Action.READ,
                    outcome=outcome,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    pii_accessed=include_pii,
                    error_message=error_msg,
                    metadata={
                        "function": func.__name__,
                        "duration_ms": round(duration_ms, 2),
                    },
                )

                try:
                    await audit_service.log(entry)
                except Exception:
                    pass

        return wrapper

    return decorator


def audit_modification(table_name: str, operation: str):
    """
    Decorator for auditing data modifications.

    Usage:
        @audit_modification(table_name="documents", operation="UPDATE")
        async def update_document(doc_id: UUID, updates: dict):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            audit_service: Optional[AuditService] = kwargs.get("audit_service")
            request: Optional[Request] = kwargs.get("request")

            if not audit_service or not request:
                return await func(*args, **kwargs)

            user_id = getattr(request.state, "user_id", None)
            user_email = getattr(request.state, "user_email", None)
            client_info = extract_client_info(request)

            # Capture old values if UPDATE or DELETE
            old_values = None
            if operation in ["UPDATE", "DELETE"]:
                # You'll need to fetch old values before modification
                # This is operation-specific
                pass

            try:
                result = await func(*args, **kwargs)
                outcome = EventOutcome.SUCCESS
                error_msg = None
                return result

            except Exception as e:
                outcome = EventOutcome.FAILURE
                error_msg = str(e)
                raise

            finally:
                # Log to main audit
                main_entry = AuditLogEntry(
                    user_id=user_id,
                    user_email=user_email,
                    session_id=client_info["session_id"],
                    ip_address=client_info["ip_address"],
                    user_agent=client_info["user_agent"],
                    event_category=EventCategory.MODIFICATION,
                    event_type=f"{table_name}_{operation.lower()}",
                    action=(
                        Action[operation]
                        if operation in Action.__members__
                        else Action.WRITE
                    ),
                    outcome=outcome,
                    resource_type=table_name,
                    error_message=error_msg,
                    metadata={"function": func.__name__},
                )

                try:
                    log_id = await audit_service.log(main_entry)

                    # Log detailed modification if success
                    if outcome == EventOutcome.SUCCESS:
                        from .audit_service import ModificationAuditEntry

                        mod_entry = ModificationAuditEntry(
                            user_id=user_id,
                            table_name=table_name,
                            record_id=kwargs.get("record_id")
                            or kwargs.get(f"{table_name[:-1]}_id"),
                            operation=operation,
                            old_values=old_values,
                            new_values=kwargs.get("updates") or kwargs.get("data"),
                        )

                        await audit_service.log_modification(log_id, mod_entry)

                except Exception:
                    pass

        return wrapper

    return decorator


def audit_authorization(func: Callable):
    """
    Decorator for auditing authorization checks.

    Usage:
        @audit_authorization
        async def check_document_access(user: User, doc_id: UUID):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        audit_service: Optional[AuditService] = kwargs.get("audit_service")
        request: Optional[Request] = kwargs.get("request")

        if not audit_service or not request:
            return await func(*args, **kwargs)

        user_id = getattr(request.state, "user_id", None)
        user_email = getattr(request.state, "user_email", None)
        client_info = extract_client_info(request)

        try:
            result = await func(*args, **kwargs)
            # Result should be a boolean (granted or not)
            granted = bool(result)
            outcome = EventOutcome.SUCCESS if granted else EventOutcome.FAILURE
            error_msg = None if granted else "Access denied"
            return result

        except Exception as e:
            outcome = EventOutcome.FAILURE
            error_msg = str(e)
            raise

        finally:
            entry = AuditLogEntry(
                user_id=user_id,
                user_email=user_email,
                session_id=client_info["session_id"],
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                event_category=EventCategory.AUTHORIZATION,
                event_type="permission_check",
                action=Action.READ,
                outcome=outcome,
                error_message=error_msg,
                metadata={
                    "function": func.__name__,
                    "granted": "result" in locals() and result,
                },
            )

            try:
                await audit_service.log(entry)
            except Exception:
                pass

    return wrapper


# ============================================
#           CONTEXT MANAGERS
# ============================================


class AuditContext:
    """
    Context manager for complex operations that need fine-grained audit control.

    Usage:
        async with AuditContext(audit_service, user_id, "document_processing") as ctx:
            # Do work
            ctx.add_metadata("chunks_processed", 50)
            ctx.mark_pii_accessed(["email", "phone"])
    """

    def __init__(
        self,
        audit_service: AuditService,
        user_id: UUID,
        user_email: str,
        operation: str,
        event_category: EventCategory = EventCategory.DATA_ACCESS,
        ip_address: Optional[str] = None,
    ):
        self.audit_service = audit_service
        self.user_id = user_id
        self.user_email = user_email
        self.operation = operation
        self.event_category = event_category
        self.ip_address = ip_address

        self.metadata = {}
        self.pii_accessed = False
        self.pii_types = []
        self.outcome = EventOutcome.SUCCESS
        self.error_message = None
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.outcome = EventOutcome.FAILURE
            self.error_message = str(exc_val)

        duration_ms = (time.time() - self.start_time) * 1000
        self.metadata["duration_ms"] = round(duration_ms, 2)

        entry = AuditLogEntry(
            user_id=self.user_id,
            user_email=self.user_email,
            ip_address=self.ip_address,
            event_category=self.event_category,
            event_type=self.operation,
            action=Action.EXECUTE,
            outcome=self.outcome,
            pii_accessed=self.pii_accessed,
            pii_types=self.pii_types if self.pii_types else None,
            error_message=self.error_message,
            metadata=self.metadata,
        )

        try:
            await self.audit_service.log(entry)
        except Exception:
            pass

        return False  # Don't suppress exceptions

    def add_metadata(self, key: str, value: any):
        """Add metadata to the audit entry"""
        self.metadata[key] = value

    def mark_pii_accessed(self, pii_types: list):
        """Mark that PII was accessed"""
        self.pii_accessed = True
        self.pii_types = pii_types

    def set_outcome(self, outcome: EventOutcome, error_msg: Optional[str] = None):
        """Manually set outcome"""
        self.outcome = outcome
        if error_msg:
            self.error_message = error_msg
