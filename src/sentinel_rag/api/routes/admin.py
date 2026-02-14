"""
Admin API routes for system management and monitoring.

- Audit logging not implemented yet !!!

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
from sentinel_rag.api.schemas import UserCreateRequest, UserDetailResponse


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


@router.post("/users/create", response_model=UserDetailResponse)
async def create_user(
    user_data: UserCreateRequest,
    db: DatabaseDep,
    admin: UserContext = AdminUserDep,
):
    """
    Create a new user in the system.
    Returns the created user's info including ID, email, role, department, permission level.
    """
    # Validate informations
    all_departments = db.get_all_departments()
    if user_data.user_department not in all_departments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid department '{user_data.user_department}'. Valid departments: {', '.join(all_departments)}",
        )

    department_roles = db.get_roles_by_department(user_data.user_department)
    if user_data.user_role not in department_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{user_data.user_role}' for department '{user_data.user_department}'. Valid roles: {', '.join(department_roles)}",
        )

    all_permission_levels = db.get_all_permission_levels()
    if user_data.user_type not in all_permission_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission level '{user_data.user_type}'. Valid levels: {', '.join(all_permission_levels)}",
        )

    # Check if user already exists
    existing_user = db.get_user_by_email(user_data.user_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{user_data.user_email}' already exists",
        )

    try:
        permission_level_id = db.create_permission_level(user_data.user_type)

        user_id = db.create_user(
            email=user_data.user_email,
            full_name=user_data.user_full_name,
            permission_level_id=permission_level_id,
        )

        db.assign_role(
            user_id=user_id,
            role_name=user_data.user_role,
            department_name=user_data.user_department,
        )

        created_user = db.get_user_by_email(user_data.user_email)

        return UserDetailResponse(
            user_id=created_user["user_id"],
            user_email=created_user["email"],
            user_full_name=created_user["full_name"],
            user_role=user_data.user_role,
            user_department=user_data.user_department,
            permission_level=user_data.user_type,
            created_at=created_user.get("created_at"),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


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
