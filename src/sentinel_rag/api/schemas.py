from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        str_strip_whitespace = True


class TimestampMixin(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


#           USER
# ---------------------------


class UserResponse(BaseSchema):
    user_id: UUID
    user_email: EmailStr
    user_role: str
    user_department: str


#           DOCUMENT
# ----------------------------


class DocumentUploadResponse(BaseSchema):
    """Response after successful document upload."""

    doc_id: UUID
    doc_classification: str
    doc_department: str
    uploaded_by: EmailStr
    processing_time_ms: Optional[float] = None


class DocumentMetadata(BaseSchema):
    """Document metadata from db."""

    doc_id: Optional[UUID] = None
    chunk_id: Optional[UUID] = None
    title: Optional[str] = None
    classification: Optional[str] = None
    department: Optional[str] = None


class DocumentResponse(BaseSchema):
    """Response model for document/chunk content."""

    page_content: str
    metadata: Dict[str, Any]


class DocumentListItem(BaseSchema, TimestampMixin):
    """Document item in list response."""

    doc_id: UUID
    title: str
    classification: str
    department: str
    chunk_count: Optional[int] = None


#           QUERY
# ---------------------------


class QueryRequest(BaseSchema):
    """Request model for RAG queries."""

    user_query: str = Field(min_length=1, max_length=5000)

    @field_validator("user_query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        return v.strip()


class QueryResponse(BaseSchema):
    """Response model for RAG queries."""

    results: List[DocumentResponse]
    query_id: Optional[str] = None
    total_results: int
    processing_time_ms: float
    pii_detected: bool = False


class QueryAuditInfo(BaseSchema):
    chunks_retrieved: int
    documents_accessed: List[str]
    vector_search_time_ms: float
    pii_types_found: List[str] = Field(default_factory=list)


#           HEALTH CHECK
# -----------------------------------


class HealthResponse(BaseSchema):
    status: str = "healthy"
    version: str
    environment: str
    audit_enabled: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DetailedHealthResponse(HealthResponse):
    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


#           ERROR
# ---------------------------


class ErrorDetail(BaseSchema):
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseSchema):
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationErrorResponse(ErrorResponse):
    error: str = "validation_error"
    validation_errors: List[Dict[str, Any]] = Field(default_factory=list)
