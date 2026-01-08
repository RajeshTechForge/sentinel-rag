from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


#       BASE MODELS
# -------------------------


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    class Config:
        from_attributes = True  # Enable ORM mode
        str_strip_whitespace = True  # Auto-strip strings


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


#           USER
# ---------------------------


class UserResponse(BaseSchema):
    """Response model for user data."""

    user_id: str
    user_email: EmailStr
    user_role: str
    user_department: str


#           DOCUMENT
# ----------------------------


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


#           QUERY
# ---------------------------


class QueryRequest(BaseSchema):
    """Request model for RAG queries."""

    user_query: str = Field(min_length=1, max_length=5000)
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


#           HEALTH CHECK
# -----------------------------------


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


#           ERROR
# ---------------------------


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
