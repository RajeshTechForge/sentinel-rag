"""
Audit Logging Service for Compliance (GDPR, SOC 2, HIPAA)
Handles all audit trail requirements for enterprise RAG system
"""

import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import asyncpg
from fastapi import Request
from pydantic import BaseModel, Field


# ============================================
# ENUMS FOR TYPE SAFETY
# ============================================


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


# ============================================
# PYDANTIC MODELS
# ============================================


class AuditLogEntry(BaseModel):
    """Main audit log entry model"""

    # Actor information
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
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
    email: str
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


# ============================================
# AUDIT SERVICE CLASS
# ============================================


class AuditService:
    """
    Central audit logging service for compliance requirements.
    Thread-safe and optimized for high-volume logging.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    # ----------------------------------------
    # MAIN AUDIT LOG
    # ----------------------------------------

    async def log(self, entry: AuditLogEntry) -> UUID:
        """
        Log an audit event to the database.
        Returns the log_id for reference in related tables.
        """
        query = """
            INSERT INTO audit_logs (
                user_id, user_email, session_id, ip_address, user_agent,
                event_category, event_type, action, outcome,
                resource_type, resource_id, resource_name,
                department_id, department_name, role_id, role_name,
                classification_level, pii_accessed, pii_types, data_redacted,
                changes, query_text, error_message, metadata, retention_years
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                $21, $22, $23, $24, $25
            ) RETURNING log_id
        """

        async with self.db_pool.acquire() as conn:
            log_id = await conn.fetchval(
                query,
                entry.user_id,
                entry.user_email,
                entry.session_id,
                entry.ip_address,
                entry.user_agent,
                entry.event_category.value,
                entry.event_type,
                entry.action.value,
                entry.outcome.value,
                entry.resource_type.value if entry.resource_type else None,
                entry.resource_id,
                entry.resource_name,
                entry.department_id,
                entry.department_name,
                entry.role_id,
                entry.role_name,
                entry.classification_level,
                entry.pii_accessed,
                json.dumps(entry.pii_types) if entry.pii_types else None,
                entry.data_redacted,
                json.dumps(entry.changes) if entry.changes else None,
                entry.query_text,
                entry.error_message,
                json.dumps(entry.metadata) if entry.metadata else None,
                entry.retention_years,
            )

        return log_id

    # ----------------------------------------
    # QUERY AUDIT
    # ----------------------------------------

    async def log_query(self, main_log_id: UUID, entry: QueryAuditEntry) -> UUID:
        """Log RAG query-specific audit information"""
        query_text_hash = hashlib.sha256(entry.query_text.encode()).hexdigest()

        query = """
            INSERT INTO query_audit (
                log_id, user_id, query_text_hash,
                chunks_retrieved, chunks_accessed, documents_accessed,
                vector_search_time_ms, llm_processing_time_ms,
                total_response_time_ms, filters_applied,
                chunks_filtered, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            ) RETURNING query_id
        """

        async with self.db_pool.acquire() as conn:
            query_id = await conn.fetchval(
                query,
                main_log_id,
                entry.user_id,
                query_text_hash,
                entry.chunks_retrieved,
                entry.chunks_accessed,
                entry.documents_accessed,
                entry.vector_search_time_ms,
                entry.llm_processing_time_ms,
                entry.total_response_time_ms,
                json.dumps(entry.filters_applied) if entry.filters_applied else None,
                entry.chunks_filtered,
                json.dumps(entry.metadata) if entry.metadata else None,
            )

        return query_id

    # ----------------------------------------
    # AUTH AUDIT
    # ----------------------------------------

    async def log_auth(self, main_log_id: UUID, entry: AuthAuditEntry) -> UUID:
        """Log authentication event"""
        query = """
            INSERT INTO auth_audit (
                log_id, user_id, email, auth_method, event_type,
                ip_address, user_agent, geolocation,
                failed_attempts_count, account_locked, mfa_used, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            ) RETURNING auth_id
        """

        async with self.db_pool.acquire() as conn:
            auth_id = await conn.fetchval(
                query,
                main_log_id,
                entry.user_id,
                entry.email,
                entry.auth_method,
                entry.event_type,
                entry.ip_address,
                entry.user_agent,
                json.dumps(entry.geolocation) if entry.geolocation else None,
                entry.failed_attempts_count,
                entry.account_locked,
                entry.mfa_used,
                json.dumps(entry.metadata) if entry.metadata else None,
            )

        return auth_id

    # ----------------------------------------
    # MODIFICATION AUDIT
    # ----------------------------------------

    async def log_modification(
        self, main_log_id: UUID, entry: ModificationAuditEntry
    ) -> UUID:
        """Log data modification event"""
        query = """
            INSERT INTO modification_audit (
                log_id, user_id, table_name, record_id, operation,
                old_values, new_values, changed_fields,
                reason, approved_by, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            ) RETURNING modification_id
        """

        async with self.db_pool.acquire() as conn:
            mod_id = await conn.fetchval(
                query,
                main_log_id,
                entry.user_id,
                entry.table_name,
                entry.record_id,
                entry.operation,
                json.dumps(entry.old_values) if entry.old_values else None,
                json.dumps(entry.new_values) if entry.new_values else None,
                entry.changed_fields,
                entry.reason,
                entry.approved_by,
                json.dumps(entry.metadata) if entry.metadata else None,
            )

        return mod_id

    # ----------------------------------------
    # CONVENIENCE METHODS
    # ----------------------------------------

    async def log_document_access(
        self,
        user_id: UUID,
        user_email: str,
        document_id: UUID,
        document_name: str,
        classification: str,
        department_name: str,
        role_name: str,
        outcome: EventOutcome,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        pii_accessed: bool = False,
        pii_types: Optional[List[str]] = None,
    ) -> UUID:
        """Convenience method for logging document access"""
        entry = AuditLogEntry(
            user_id=user_id,
            user_email=user_email,
            session_id=session_id,
            ip_address=ip_address,
            event_category=EventCategory.DATA_ACCESS,
            event_type="document_access",
            action=Action.READ,
            outcome=outcome,
            resource_type=ResourceType.DOCUMENT,
            resource_id=document_id,
            resource_name=document_name,
            department_name=department_name,
            role_name=role_name,
            classification_level=classification,
            pii_accessed=pii_accessed,
            pii_types=pii_types,
        )
        return await self.log(entry)

    async def log_permission_check(
        self,
        user_id: UUID,
        user_email: str,
        resource_type: ResourceType,
        resource_id: UUID,
        required_role: str,
        user_role: str,
        granted: bool,
        ip_address: Optional[str] = None,
    ) -> UUID:
        """Convenience method for logging permission checks"""
        entry = AuditLogEntry(
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            event_category=EventCategory.AUTHORIZATION,
            event_type="permission_check",
            action=Action.READ,
            outcome=EventOutcome.SUCCESS if granted else EventOutcome.FAILURE,
            resource_type=resource_type,
            resource_id=resource_id,
            role_name=user_role,
            metadata={"required_role": required_role, "granted": granted},
        )
        return await self.log(entry)

    async def log_failed_login(
        self, email: str, ip_address: str, reason: str, failed_attempts: int = 1
    ) -> UUID:
        """Convenience method for failed login attempts"""
        # Log to main audit
        main_entry = AuditLogEntry(
            user_email=email,
            ip_address=ip_address,
            event_category=EventCategory.AUTHENTICATION,
            event_type="login_failure",
            action=Action.LOGIN,
            outcome=EventOutcome.FAILURE,
            error_message=reason,
        )
        log_id = await self.log(main_entry)

        # Log to auth audit
        auth_entry = AuthAuditEntry(
            email=email,
            auth_method="email_password",
            event_type="login_failure",
            ip_address=ip_address,
            failed_attempts_count=failed_attempts,
        )
        await self.log_auth(log_id, auth_entry)

        return log_id

    # ----------------------------------------
    # QUERY METHODS FOR COMPLIANCE REPORTS
    # ----------------------------------------

    async def get_user_activity(
        self, user_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get all activity for a user (GDPR Article 15 - Right to Access)"""
        query = """
            SELECT 
                log_id, timestamp, event_category, event_type,
                action, outcome, resource_type, resource_name,
                classification_level, pii_accessed
            FROM audit_logs
            WHERE user_id = $1
                AND timestamp BETWEEN $2 AND $3
            ORDER BY timestamp DESC
        """

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, user_id, start_date, end_date)

        return [dict(row) for row in rows]

    async def get_pii_access_log(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get all PII access events (GDPR, HIPAA compliance)"""
        query = """
            SELECT 
                log_id, timestamp, user_email, event_type,
                resource_type, resource_name, pii_types,
                data_redacted, department_name, role_name
            FROM audit_logs
            WHERE pii_accessed = TRUE
                AND timestamp BETWEEN $1 AND $2
            ORDER BY timestamp DESC
        """

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, start_date, end_date)

        return [dict(row) for row in rows]

    async def get_failed_access_attempts(
        self, start_date: datetime, end_date: datetime, limit: int = 100
    ) -> List[Dict]:
        """Get failed access attempts (SOC 2 security monitoring)"""
        query = """
            SELECT 
                log_id, timestamp, user_email, ip_address,
                event_category, event_type, resource_type,
                resource_name, error_message
            FROM audit_logs
            WHERE outcome = 'failure'
                AND timestamp BETWEEN $1 AND $2
            ORDER BY timestamp DESC
            LIMIT $3
        """

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, start_date, end_date, limit)

        return [dict(row) for row in rows]

    async def get_data_modifications(
        self, table_name: str, record_id: UUID, start_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get modification history for a record (audit trail)"""
        if start_date:
            query = """
                SELECT 
                    m.modification_id, m.timestamp, m.operation,
                    m.old_values, m.new_values, m.changed_fields,
                    m.reason, a.user_email
                FROM modification_audit m
                JOIN audit_logs a ON m.log_id = a.log_id
                WHERE m.table_name = $1 
                    AND m.record_id = $2
                    AND m.timestamp >= $3
                ORDER BY m.timestamp DESC
            """
            params = (table_name, record_id, start_date)
        else:
            query = """
                SELECT 
                    m.modification_id, m.timestamp, m.operation,
                    m.old_values, m.new_values, m.changed_fields,
                    m.reason, a.user_email
                FROM modification_audit m
                JOIN audit_logs a ON m.log_id = a.log_id
                WHERE m.table_name = $1 AND m.record_id = $2
                ORDER BY m.timestamp DESC
            """
            params = (table_name, record_id)

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [dict(row) for row in rows]

    async def archive_old_logs(self, cutoff_date: datetime) -> int:
        """Archive logs older than retention period"""
        query = """
            UPDATE audit_logs
            SET archived = TRUE, archived_at = CURRENT_TIMESTAMP
            WHERE timestamp < $1
                AND archived = FALSE
            RETURNING log_id
        """

        async with self.db_pool.acquire() as conn:
            result = await conn.fetch(query, cutoff_date)

        return len(result)


# ============================================
# HELPER FUNCTIONS
# ============================================


def extract_client_info(request: Request) -> Dict[str, Optional[str]]:
    """Extract client information from FastAPI request"""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "session_id": request.cookies.get("session_id"),
    }


def get_retention_years(classification: str) -> int:
    """
    Determine retention period based on data classification.
    Adjust based on your regulatory requirements.
    """
    retention_map = {"public": 3, "internal": 5, "confidential": 7, "restricted": 10}
    return retention_map.get(classification.lower(), 7)
