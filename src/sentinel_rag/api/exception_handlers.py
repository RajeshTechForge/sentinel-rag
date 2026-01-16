"""
Exception handlers for the Sentinel RAG API.
"""

import logging
import traceback
from uuid import uuid4
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sentinel_rag.exceptions import SentinelError
from sentinel_rag.config import get_settings

logger = logging.getLogger(__name__)


def create_error_response(
    request_id: str,
    error: str,
    message: str,
    status_code: int,
    details: dict = None,
) -> JSONResponse:
    """Create a standardized error response."""
    content = {
        "error": error,
        "message": message,
        "request_id": request_id,
    }
    if details:
        content["details"] = details

    return JSONResponse(status_code=status_code, content=content)


async def sentinel_exception_handler(
    request: Request,
    exc: SentinelError,
) -> JSONResponse:
    """
    Handle all SentinelError exceptions.
    """
    request_id = getattr(request.state, "request_id", str(uuid4()))

    logger.warning(
        f"Business error: {exc.code}",
        extra={
            "request_id": request_id,
            "error_code": exc.code,
            "error_message": exc.message,
            "path": request.url.path,
        },
    )

    return create_error_response(
        request_id=request_id,
        error=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details if exc.details else None,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    """
    request_id = getattr(request.state, "request_id", str(uuid4()))

    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append(
            {
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.info(
        f"Validation error on {request.url.path}",
        extra={
            "request_id": request_id,
            "errors": errors,
        },
    )

    return create_error_response(
        request_id=request_id,
        error="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"validation_errors": errors},
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    Handle standard HTTP exceptions.
    """
    request_id = getattr(request.state, "request_id", str(uuid4()))

    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        408: "REQUEST_TIMEOUT",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }

    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")

    return create_error_response(
        request_id=request_id,
        error=error_code,
        message=str(exc.detail),
        status_code=exc.status_code,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle all unhandled exceptions.
    """
    request_id = getattr(request.state, "request_id", str(uuid4()))
    settings = get_settings()

    # Log full error with stack trace
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        },
        exc_info=True,
    )

    if settings.debug:
        details = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc().split("\n"),
        }
    else:
        details = None

    return create_error_response(
        request_id=request_id,
        error="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI app.
    """
    app.add_exception_handler(SentinelError, sentinel_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
