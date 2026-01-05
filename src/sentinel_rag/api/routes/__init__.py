from fastapi import APIRouter

from .users import router as users_router
from .documents import router as documents_router
from .queries import router as queries_router
from .health import router as health_router


# Create main API router
api_router = APIRouter(prefix="/api")

# Include all domain routers
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(queries_router, prefix="/query", tags=["Query"])

health_router_root = health_router
