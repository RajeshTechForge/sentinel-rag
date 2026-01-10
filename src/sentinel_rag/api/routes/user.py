from typing import List
from fastapi import APIRouter, Depends

from sentinel_rag.services.auth import get_current_active_user, UserContext
from sentinel_rag.api.schemas import UserResponse
from sentinel_rag.api.dependencies import DatabaseDep


router = APIRouter()


@router.post("", response_model=UserResponse)
async def get_user(
    user: UserContext = Depends(get_current_active_user),
):
    """
    Get current user information
    """
    return UserResponse(
        user_id=user.user_id,
        user_email=user.email,
        user_role=user.role,
        user_department=user.department,
    )


@router.post("/docs", response_model=List[dict])
async def get_user_documents(
    db: DatabaseDep,
    user: UserContext = Depends(get_current_active_user),
):
    """
    Get all documents uploaded by a current user.

    Returns a list of document metadata for documents
    the specified user has uploaded.
    """
    documents = db.get_document_uploads_by_user(user_id=str(user.user_id))
    return documents
