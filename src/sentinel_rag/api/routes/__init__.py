from fastapi import APIRouter

from .auth import router as auth_router
from .user import router as users_router
from .documents import router as documents_router
from .queries import router as queries_router
from .health import router as health_router

health_router_root = health_router

auth_router_root = APIRouter(prefix="/auth")
auth_router_root.include_router(auth_router, tags=["Auth"])

api_router = APIRouter(prefix="/api")

api_router.include_router(users_router, prefix="/user", tags=["User"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(queries_router, prefix="/query", tags=["Query"])
