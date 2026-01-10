from typing import Any, Dict, List, Optional
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, EmailStr, Field


class EventCategory(str, Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    MODIFICATION = "modification"
    ADMIN = "admin"
    SYSTEM = "system"


class EventOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class Action(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    UPDATE = "UPDATE"
    EXECUTE = "EXECUTE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"


class ResourceType(str, Enum):
    DOCUMENT = "document"
    CHUNK = "chunk"
    USER = "user"
    ROLE = "role"
    DEPARTMENT = "department"
    QUERY = "query"
    SYSTEM = "system"


#       PYDANTIC MODELS
# ---------------------------------


class AuditLogEntry(BaseModel):
    """Main audit log entry model"""

    # Actor information
    user_id: Optional[UUID] = None
    user_email: Optional[EmailStr] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Event classification
    event_category: EventCategory
    event_type: str
    action: Action
    outcome: EventOutcome

    # Resource information
    resource_type: Optional[ResourceType] = None
    resource_id: Optional[UUID] = None
    resource_name: Optional[str] = None

    # Access control context
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    role_id: Optional[UUID] = None
    role_name: Optional[str] = None
    classification_level: Optional[str] = None

    # Compliance fields
    pii_accessed: bool = False
    pii_types: Optional[List[str]] = None
    data_redacted: bool = False

    # Change tracking
    changes: Optional[Dict[str, Any]] = None

    # Additional context
    query_text: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    # Retention
    retention_years: int = 7


class QueryAuditEntry(BaseModel):
    """RAG query-specific audit entry"""

    user_id: Optional[UUID] = None
    query_text: str

    chunks_retrieved: int = 0
    chunks_accessed: List[UUID] = Field(default_factory=list)
    documents_accessed: List[UUID] = Field(default_factory=list)

    vector_search_time_ms: float = 0.0
    llm_processing_time_ms: float = 0.0
    total_response_time_ms: float = 0.0

    filters_applied: Optional[Dict[str, Any]] = None
    chunks_filtered: int = 0

    metadata: Optional[Dict[str, Any]] = None


class AuthAuditEntry(BaseModel):
    """Authentication-specific audit entry"""

    user_id: Optional[UUID] = None
    email: EmailStr
    auth_method: str
    event_type: str

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    geolocation: Optional[Dict[str, str]] = None

    failed_attempts_count: int = 0
    account_locked: bool = False
    mfa_used: bool = False

    metadata: Optional[Dict[str, Any]] = None


class ModificationAuditEntry(BaseModel):
    """Data modification audit entry"""

    user_id: Optional[UUID] = None
    table_name: str
    record_id: UUID
    operation: str  # INSERT, UPDATE, DELETE

    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    changed_fields: Optional[List[str]] = None

    reason: Optional[str] = None
    approved_by: Optional[UUID] = None

    metadata: Optional[Dict[str, Any]] = None
