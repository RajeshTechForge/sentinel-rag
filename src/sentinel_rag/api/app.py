"""
Application factory and FastAPI app initialization for sentinel-rag.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .dependencies import get_app_state, app_lifespan
from .exception_handlers import register_exception_handlers
from .routes import api_router, auth_router_root, health_router_root

from sentinel_rag.config import get_settings
from sentinel_rag.services.audit import AuditLoggingMiddleware


def create_application() -> FastAPI:
    """Creates and configures the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=app_lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    if settings.audit.enabled:
        app.add_middleware(
            AuditLoggingMiddleware,
            audit_service=lambda: get_app_state().audit_service,
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.security.secret_key,
    )

    register_exception_handlers(app)

    app.include_router(health_router_root)
    app.include_router(auth_router_root)
    app.include_router(api_router)

    return app


app = create_application()


def create_test_application(**overrides) -> FastAPI:
    """Creates an application instance for testing purposes."""
    return create_application()
