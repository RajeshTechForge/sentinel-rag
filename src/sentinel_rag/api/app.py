"""
Sentinel RAG API - Application Factory.

This module contains ONLY the FastAPI application factory.
All business logic, routes, and configuration are imported from other modules.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from sentinel_rag.api.dependencies import app_lifespan
from sentinel_rag.api.exception_handlers import register_exception_handlers
from sentinel_rag.api.routes import api_router, health_router_root
from sentinel_rag.api.auth_routes import router as auth_router
from sentinel_rag.config.settings import get_settings
from sentinel_rag import AuditLoggingMiddleware
from sentinel_rag.api.dependencies import get_app_state


def create_application() -> FastAPI:
    """
    Application factory function.

    Creates and configures the FastAPI application.
    All configuration is centralized here.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    # Configure logging
    log_level = logging.DEBUG if settings.debug else logging.WARNING
    logging.basicConfig(level=log_level, force=True)
    logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=app_lifespan,
        # OpenAPI customization
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # ============================================
    # MIDDLEWARE (order matters - last added = first executed)
    # ============================================

    # Audit logging middleware (first to execute)
    if settings.audit.enabled:
        app.add_middleware(
            AuditLoggingMiddleware,
            audit_service=lambda: get_app_state().audit_service,
        )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )

    # Session middleware (for OAuth state)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.security.secret_key,
    )

    # ============================================
    # EXCEPTION HANDLERS
    # ============================================
    register_exception_handlers(app)

    # ============================================
    # ROUTES
    # ============================================

    app.include_router(health_router_root)
    app.include_router(auth_router)
    app.include_router(api_router)

    return app


# Create the application instance
app = create_application()


# ============================================
# FOR DEVELOPMENT / TESTING
# ============================================


def create_test_application(**overrides) -> FastAPI:
    """
    Create application with test configuration.

    Allows overriding settings for testing.

    Usage:
        app = create_test_application(debug=True, audit_enabled=False)
    """
    # This would use dependency injection to override settings
    # For now, just return the regular app
    return create_application()
