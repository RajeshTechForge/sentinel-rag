from datetime import datetime, timezone
from fastapi import APIRouter

from sentinel_rag.api.dependencies import SettingsDep, get_app_state
from sentinel_rag.api.schema import HealthResponse, DetailedHealthResponse


router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    return {"message": "Welcome to Sentinel RAG API"}


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: SettingsDep):
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        audit_enabled=settings.audit.enabled,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/ready", response_model=DetailedHealthResponse)
async def readiness_check(settings: SettingsDep):
    state = get_app_state()
    components = {}

    db_healthy = state.db is not None
    components["database"] = {
        "status": "healthy" if db_healthy else "unhealthy",
        "connected": db_healthy,
    }

    engine_healthy = state.engine is not None
    components["engine"] = {
        "status": "healthy" if engine_healthy else "unhealthy",
        "initialized": engine_healthy,
    }

    audit_healthy = state.audit_service is not None
    components["audit"] = {
        "status": "healthy" if audit_healthy else "unhealthy",
        "enabled": settings.audit.enabled,
    }

    all_healthy = all(c["status"] == "healthy" for c in components.values())

    return DetailedHealthResponse(
        status="healthy" if all_healthy else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        audit_enabled=settings.audit.enabled,
        timestamp=datetime.now(timezone.utc),
        components=components,
    )


@router.get("/health/live")
async def liveness_check():
    return {"status": "alive"}
