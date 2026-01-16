"""
This module defines the API routes for querying documents using RAG.

- Audit logging is integrated.

"""

import re
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends

from sentinel_rag.api.dependencies import get_current_active_user
from sentinel_rag.services.auth import UserContext
from sentinel_rag.services.audit import (
    AuditLogEntry,
    QueryAuditEntry,
    EventCategory,
    EventOutcome,
    Action,
)

from sentinel_rag.api.schemas import QueryRequest, DocumentResponse
from sentinel_rag.exceptions import DocumentProcessingError
from sentinel_rag.api.dependencies import (
    EngineDep,
    AuditServiceDep,
    RequestContextDep,
)


router = APIRouter()


@router.post("", response_model=List[DocumentResponse])
async def query_documents(
    request: QueryRequest,
    engine: EngineDep,
    audit: AuditServiceDep,
    context: RequestContextDep,
    user: UserContext = Depends(get_current_active_user),
):
    """
    Query documents using RAG.

    Performs a semantic search across documents the user has access to,
    applying RBAC and tenant isolation.
    """
    start_time = datetime.now()

    # Update context with authenticated user
    context.user_id = user.user_id
    context.user_email = user.email
    context.tenant_id = user.tenant_id

    try:
        results = engine.query(
            request.user_query,
            user_id=user.user_id,
        )

        vector_time = (datetime.now() - start_time).total_seconds() * 1000

        # Detect PII in results
        pii_detected = False
        pii_types_found = []

        for doc in results:
            content = doc.page_content
            if "<" in content and ">" in content:
                pii_detected = True
                pii_matches = re.findall(r"<([A-Z_]+)>", content)
                pii_types_found.extend(pii_matches)

        pii_types_found = list(set(pii_types_found))

        # Extract accessed documents and chunks
        docs_accessed = list(
            set(
                doc.metadata.get("doc_id")
                for doc in results
                if doc.metadata.get("doc_id")
            )
        )

        chunks_accessed = list(
            set(
                doc.metadata.get("chunk_id")
                for doc in results
                if doc.metadata.get("chunk_id")
            )
        )

        total_time = (datetime.now() - start_time).total_seconds() * 1000

        # Log main audit entry
        main_entry = AuditLogEntry(
            user_id=user.user_id,
            user_email=user.email,
            ip_address=context.client_ip,
            user_agent=context.user_agent,
            session_id=context.session_id,
            event_category=EventCategory.DATA_ACCESS,
            event_type="rag_query",
            action=Action.READ,
            outcome=EventOutcome.SUCCESS,
            query_text=request.user_query[:500],  # Truncate for storage
            pii_accessed=pii_detected,
            pii_types=pii_types_found if pii_detected else None,
            data_redacted=pii_detected,
            metadata={
                "chunks_retrieved": len(results),
                "total_time_ms": round(total_time, 2),
                "tenant_id": user.tenant_id,
            },
        )
        log_id = await audit.log(main_entry)

        # Log query-specific audit
        query_entry = QueryAuditEntry(
            user_id=user.user_id,
            query_text=request.user_query,
            chunks_retrieved=len(results),
            chunks_accessed=chunks_accessed,
            documents_accessed=docs_accessed,
            vector_search_time_ms=vector_time,
            llm_processing_time_ms=0.0,  # No LLM yet
            total_response_time_ms=round(total_time, 2),
            filters_applied={
                "user_id": user.user_id,
                "tenant_id": user.tenant_id,
            },
            chunks_filtered=0,
        )
        await audit.log_query(log_id, query_entry)

        return [
            DocumentResponse(page_content=doc.page_content, metadata=doc.metadata)
            for doc in results
        ]

    except Exception as e:
        # Log failed query
        await audit.log(
            AuditLogEntry(
                user_id=user.user_id,
                user_email=user.email,
                ip_address=context.client_ip,
                event_category=EventCategory.DATA_ACCESS,
                event_type="rag_query",
                action=Action.READ,
                outcome=EventOutcome.FAILURE,
                query_text=request.user_query[:500],
                error_message=str(e),
            )
        )
        raise DocumentProcessingError(f"Query failed: {str(e)}") from e
