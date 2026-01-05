"""
Request/Response Schemas Module.

Separating schemas provides:
- Single source of truth for data contracts
- Easy versioning (v1/v2 schemas)
- Reusability across endpoints
- Clear API documentation
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================
# BASE MODELS
# ============================================


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    class Config:
        from_attributes = True  # Enable ORM mode
        str_strip_whitespace = True  # Auto-strip strings


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================
# USER SCHEMAS
# ============================================


class UserBase(BaseSchema):
    """Base user schema with shared fields."""

    user_email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserLoginRequest(BaseSchema):
    """Request model for user login/lookup."""

    user_email: EmailStr
    user_id: Optional[str] = None  # Optional for backward compatibility


class UserCreateRequest(UserBase):
    """Request model for creating a new user."""

    user_role: str = Field(min_length=1, max_length=100)
    user_department: str = Field(min_length=1, max_length=100)

    @field_validator("user_role", "user_department")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()


class UserResponse(UserBase):
    """Response model for user data."""

    user_id: str
    user_role: str
    user_department: str


class UserDocumentsRequest(BaseSchema):
    """Request for fetching user's documents."""

    user_email: EmailStr


# ============================================
# DOCUMENT SCHEMAS
# ============================================


class DocumentUploadRequest(BaseSchema):
    """
    Document upload metadata.
    Note: File is handled separately via UploadFile.
    """

    doc_title: str = Field(min_length=1, max_length=500)
    doc_description: str = Field(max_length=2000, default="")
    user_email: EmailStr
    doc_department: str = Field(min_length=1, max_length=100)
    doc_classification: str = Field(min_length=1, max_length=50)

    @field_validator("doc_classification")
    @classmethod
    def validate_classification(cls, v: str) -> str:
        valid_classifications = {"public", "internal", "confidential", "restricted"}
        if v.lower() not in valid_classifications:
            raise ValueError(f"Classification must be one of: {valid_classifications}")
        return v.lower()


class DocumentUploadResponse(BaseSchema):
    """Response after successful document upload."""

    doc_id: str
    doc_classification: str
    doc_department: str
    uploaded_by: EmailStr
    processing_time_ms: Optional[float] = None


class DocumentMetadata(BaseSchema):
    """Document metadata from vector store."""

    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    title: Optional[str] = None
    classification: Optional[str] = None
    department: Optional[str] = None


class DocumentResponse(BaseSchema):
    """Response model for document/chunk content."""

    page_content: str
    metadata: Dict[str, Any]


class DocumentListItem(BaseSchema, TimestampMixin):
    """Document item in list response."""

    doc_id: str
    title: str
    classification: str
    department: str
    chunk_count: Optional[int] = None


# ============================================
# QUERY SCHEMAS
# ============================================


class QueryRequest(BaseSchema):
    """Request model for RAG queries."""

    user_query: str = Field(min_length=1, max_length=5000)
    user_email: EmailStr
    user_id: Optional[str] = None  # Optional, use authenticated user
    k: int = Field(default=5, ge=1, le=50)

    @field_validator("user_query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        # Basic sanitization - extend as needed
        return v.strip()


class QueryResponse(BaseSchema):
    """Response model for RAG queries."""

    results: List[DocumentResponse]
    query_id: Optional[str] = None
    total_results: int
    processing_time_ms: float
    pii_detected: bool = False


class QueryAuditInfo(BaseSchema):
    """Query audit information for logging."""

    chunks_retrieved: int
    documents_accessed: List[str]
    vector_search_time_ms: float
    pii_types_found: List[str] = Field(default_factory=list)


# ============================================
# HEALTH CHECK SCHEMAS
# ============================================


class HealthResponse(BaseSchema):
    """Health check response."""

    status: str = "healthy"
    version: str
    environment: str
    audit_enabled: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DetailedHealthResponse(HealthResponse):
    """Detailed health check with component status."""

    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


# ============================================
# ERROR SCHEMAS
# ============================================


class ErrorDetail(BaseSchema):
    """Detailed error information."""

    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseSchema):
    """Standard error response format."""

    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationErrorResponse(ErrorResponse):
    """Validation error response."""

    error: str = "validation_error"
    validation_errors: List[Dict[str, Any]] = Field(default_factory=list)
