"""
This module defines the dependency injection system for the Sentinel RAG API
using FastAPI.

"""

from contextlib import asynccontextmanager
from typing import Annotated, Optional, Protocol
from fastapi import Depends, HTTPException, Request, status

from sentinel_rag.core import SentinelEngine
from sentinel_rag.services.database import DatabaseManager
from sentinel_rag.services.vectorstore import QdrantStore
from sentinel_rag.services.audit import AuditService, AuditDatabaseManager
from sentinel_rag.services.auth import UserContext
from sentinel_rag.services.auth.oidc import (
    get_current_active_user as _get_current_active_user,
)
from sentinel_rag.config import AppSettings, get_settings


class IAuditService(Protocol):
    """Interface for audit service - enables easy mocking."""

    async def log(self, entry) -> str: ...

    async def log_query(self, log_id: str, entry) -> None: ...

    async def log_auth(self, log_id: str, entry) -> None: ...


class MockAuditService:
    """No-op audit service for when logging is disabled."""

    async def log(self, entry) -> str:
        return "mock_log_id"

    async def log_query(self, log_id: str, entry) -> None:
        pass

    async def log_auth(self, log_id: str, entry) -> None:
        pass


# Application State Management
# ----------------------------


class AppState:
    """
    Centralized application state container.

    Replaces scattered global variables with a single,
    type-safe state container.
    """

    def __init__(self):
        self.db: Optional[DatabaseManager] = None
        self.vector_store: Optional[QdrantStore] = None
        self.engine: Optional[SentinelEngine] = None
        self.audit_service: Optional[IAuditService] = None
        self.audit_db: Optional[AuditDatabaseManager] = None
        self._initialized: bool = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self, settings: AppSettings) -> None:
        """Initialize all application components."""
        if self._initialized:
            return

        # Initialize PostgreSQL database
        self.db = DatabaseManager(settings.database.dsn)

        # Initialize Qdrant vector store
        self.vector_store = QdrantStore(
            host=settings.qdrant.host,
            port=settings.qdrant.port,
            api_key=settings.qdrant.api_key or None,
            prefer_grpc=settings.qdrant.prefer_grpc,
            vector_size=settings.embeddings.vector_size,
        )

        # Initialize engine with both stores
        self.engine = SentinelEngine(
            db=self.db,
            vector_store=self.vector_store,
            rbac_config=settings.rbac.as_dict,
            max_retrieved_docs=settings.doc_retrieval.max_retrieved_docs,
            similarity_threshold=settings.doc_retrieval.similarity_threshold,
            rrf_constant=settings.doc_retrieval.rrf_constant,
        )

        # Initialize audit service
        if settings.audit.enabled:
            audit_dsn = settings.audit_database.get_effective_dsn(settings.database)

            self.audit_db = AuditDatabaseManager(
                database_url=audit_dsn,
                min_pool_size=settings.audit_database.min_pool_size,
                max_pool_size=settings.audit_database.max_pool_size,
            )
            await self.audit_db.initialize()
            self.audit_service = AuditService(self.audit_db.pool)
        else:
            self.audit_service = MockAuditService()

        self._initialized = True

    async def shutdown(self) -> None:
        """Clean up all resources."""
        if self.engine:
            self.engine.close()
            self.engine = None

        if self.vector_store:
            self.vector_store.close()
            self.vector_store = None

        if self.audit_db:
            await self.audit_db.close()
            self.audit_db = None

        self.db = None
        self.audit_service = None
        self._initialized = False


_app_state = AppState()


def get_app_state() -> AppState:
    return _app_state


@asynccontextmanager
async def app_lifespan(app):
    settings = get_settings()
    state = get_app_state()

    await state.initialize(settings)

    audit_status = "enabled" if settings.audit.enabled else "disabled"
    print(f"✅ Sentinel RAG API started (audit: {audit_status})")

    yield

    await state.shutdown()
    print("🛑 Sentinel RAG API shutdown complete")


#       DEPENDENCY PROVIDERS
# ------------------------------------


def get_settings_dep() -> AppSettings:
    """Dependency for settings - allows override in tests."""
    return get_settings()


SettingsDep = Annotated[AppSettings, Depends(get_settings_dep)]


def get_database(
    state: Annotated[AppState, Depends(get_app_state)],
) -> DatabaseManager:
    """Dependency for database manager."""
    if not state.db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized",
        )
    return state.db


DatabaseDep = Annotated[DatabaseManager, Depends(get_database)]


def get_engine(
    state: Annotated[AppState, Depends(get_app_state)],
) -> SentinelEngine:
    """Dependency for RAG engine."""
    if not state.engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Engine not initialized",
        )
    return state.engine


EngineDep = Annotated[SentinelEngine, Depends(get_engine)]


def get_audit_service(
    state: Annotated[AppState, Depends(get_app_state)],
) -> IAuditService:
    """Dependency for audit service."""
    if not state.audit_service:
        return MockAuditService()
    return state.audit_service


AuditServiceDep = Annotated[IAuditService, Depends(get_audit_service)]


#       REQUEST CONTEXT
# ------------------------------------


class RequestContext:
    """
    Request-scoped context containing user and request info.

    This replaces the pattern of storing data in request.state
    and provides type-safe access to request context.
    """

    def __init__(
        self,
        request: Request,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        self.request = request
        self.user_id = user_id
        self.user_email = user_email
        self.tenant_id = tenant_id

    @property
    def client_ip(self) -> Optional[str]:
        return self.request.client.host if self.request.client else None

    @property
    def user_agent(self) -> Optional[str]:
        return self.request.headers.get("user-agent")

    @property
    def session_id(self) -> Optional[str]:
        return self.request.cookies.get("session_id")

    def to_dict(self) -> dict:
        """Convert to dictionary for audit logging."""
        return {
            "ip_address": self.client_ip,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
        }


async def get_request_context(request: Request) -> RequestContext:
    """
    Dependency that creates request context.

    User info will be populated by auth middleware or route handlers.
    """
    return RequestContext(request=request)


RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]


#       AUTHENTICATION
# ------------------------------------


async def get_current_active_user(
    request: Request, settings: SettingsDep
) -> UserContext:
    """
    Dependency wrapper for authentication that injects settings.

    This wrapper ensures settings are automatically injected into the
    authentication function, maintaining backward compatibility with
    existing route handlers.
    """
    return await _get_current_active_user(request, settings)


CurrentUserDep = Annotated[UserContext, Depends(get_current_active_user)]


#       COMPOSITE DEPENDENCIES
# ------------------------------------


class ServiceContainer:
    """
    Container for commonly used services.

    Reduces boilerplate in route handlers by bundling
    frequently used dependencies together.
    """

    def __init__(
        self,
        db: DatabaseManager,
        engine: SentinelEngine,
        audit: IAuditService,
        settings: AppSettings,
        context: RequestContext,
    ):
        self.db = db
        self.engine = engine
        self.audit = audit
        self.settings = settings
        self.context = context


async def get_services(
    db: DatabaseDep,
    engine: EngineDep,
    audit: AuditServiceDep,
    settings: SettingsDep,
    context: RequestContextDep,
) -> ServiceContainer:
    """Dependency that bundles all services."""
    return ServiceContainer(
        db=db,
        engine=engine,
        audit=audit,
        settings=settings,
        context=context,
    )


ServicesDep = Annotated[ServiceContainer, Depends(get_services)]
