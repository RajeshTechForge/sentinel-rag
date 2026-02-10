"""
Admin API routes for system management and monitoring.

Provides endpoints for:
- Audit log access
- User management
- Document oversight
- System health and metrics
- Database statistics
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status

from sentinel_rag.api.dependencies import (
    DatabaseDep,
    EngineDep,
    get_current_active_user,
)
from sentinel_rag.services.auth import UserContext


router = APIRouter()


#               ADMIN AUTHORIZATION
# --------------------------------------------------


async def require_admin(
    db: DatabaseDep,
    user: UserContext = Depends(get_current_active_user),
) -> UserContext:
    permission_level = db.get_user_permission_level(user.user_id)
    if not permission_level or permission_level.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this operation",
        )
    return user


AdminUserDep = Depends(require_admin)


#            USER MANAGEMENT ENDPOINTS
# --------------------------------------------------


@router.get("/users", response_model=List[dict])
async def list_all_users(
    db: DatabaseDep,
    admin: UserContext = AdminUserDep,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    department: Optional[str] = Query(None, description="Filter by department"),
    role: Optional[str] = Query(None, description="Filter by role"),
):
    """
    List all users in the system with pagination.
    Returns user information including ID, email, role, and department.
    """
    pass


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    db: DatabaseDep,
    admin: UserContext = AdminUserDep,
):
    """
    Get detailed information about a specific user.

    Returns comprehensive user information including:
    - User profile
    - Role and department
    - Document upload count
    - Recent activity
    """
    pass


#               AUDIT LOG ENDPOINTS
# --------------------------------------------------


@router.get("/audit-logs")
async def get_audit_logs(
    db: DatabaseDep,
    admin: UserContext = AdminUserDep,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
):
    """
    Retrieve audit logs with filtering and pagination.

    Returns paginated audit log entries with optional filters for:
    - User ID
    - Action type
    - Date range
    """
    pass

@router.get("/audit-logs/stats")
async def get_audit_stats(
    db: DatabaseDep,
    admin: UserContext = AdminUserDep,
):
    """
    Get audit log statistics and metrics.

    Returns aggregated statistics including:
    - Total log entries
    - Actions by type
    - Most active users
    """
    pass


#           DOCUMENT MANAGEMENT ENDPOINTS
# --------------------------------------------------


@router.get("/documents")
async def list_all_documents(
    db: DatabaseDep,
    admin: UserContext = AdminUserDep,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    department: Optional[str] = Query(None, description="Filter by department"),
    classification: Optional[str] = Query(None, description="Filter by classification"),
    uploaded_by: Optional[str] = Query(None, description="Filter by uploader user ID"),
):
    """
    List all documents across all users (admin view).
    Provides cross-user document visibility with filtering options.
    """
    pass


@router.get("/documents/stats")
async def get_document_stats(
    db: DatabaseDep,
    admin: UserContext = AdminUserDep,
):
    """
    Get document statistics and distribution.
    Returns aggregated statistics about documents in the system.
    """
    pass


#           SYSTEM & DATABASE ENDPOINTS
# --------------------------------------------------


@router.get("/system/health")
async def get_system_health(
    db: DatabaseDep,
    engine: EngineDep,
    admin: UserContext = AdminUserDep,
):
    """
    Get detailed system health metrics.
    Returns health status of all system components.
    """
    pass


@router.get("/system/stats")
async def get_system_stats(
    db: DatabaseDep,
    engine: EngineDep,
    admin: UserContext = AdminUserDep,
):
    """
    Get comprehensive system statistics.
    Returns metrics about database, vector store, and system usage.
    """
    pass


@router.get("/database/stats")
async def get_database_stats(
    db: DatabaseDep,
    admin: UserContext = AdminUserDep,
):
    """
    Get detailed database statistics and table information.
    Returns information about database tables, sizes, and row counts.
    """
    pass