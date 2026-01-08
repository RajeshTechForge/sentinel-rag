from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, UploadFile

from sentinel_rag.services.auth import get_current_active_user, UserContext
from sentinel_rag.services.audit import (
    AuditLogEntry,
    EventCategory,
    EventOutcome,
    Action,
    ResourceType,
)

from sentinel_rag.exceptions import DocumentProcessingError
from sentinel_rag.api.schema import DocumentUploadResponse
from sentinel_rag.api.dependencies import (
    EngineDep,
    AuditServiceDep,
    RequestContextDep,
)


router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    engine: EngineDep,
    audit: AuditServiceDep,
    context: RequestContextDep,
    file: UploadFile = File(...),
    doc_title: str = Form(...),
    doc_description: str = Form(...),
    doc_department: str = Form(...),
    doc_classification: str = Form(...),
    user: UserContext = Depends(get_current_active_user),
):
    """
    Upload and process a document.

    The document will be:
    1. Validated for user and department
    2. Processed and chunked
    3. Stored in the vector database
    4. Logged for audit compliance
    """
    # Update context with authenticated user
    context.user_id = user.user_id
    context.user_email = user.email
    context.tenant_id = user.tenant_id

    start_time = datetime.now()

    try:
        doc_id = engine.ingest_documents(
            source=file,
            title=doc_title,
            description=doc_description,
            user_id=user.user_id,
            department_id=doc_department,
            classification=doc_classification,
        )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Log successful upload
        await audit.log(
            AuditLogEntry(
                user_id=user.user_id,
                user_email=user.email,
                ip_address=context.client_ip,
                user_agent=context.user_agent,
                session_id=context.session_id,
                event_category=EventCategory.MODIFICATION,
                event_type="document_upload",
                action=Action.WRITE,
                outcome=EventOutcome.SUCCESS,
                resource_type=ResourceType.DOCUMENT,
                resource_id=doc_id,
                resource_name=file.filename,
                department_name=doc_department,
                classification_level=doc_classification,
                metadata={
                    "title": doc_title,
                    "description": doc_description,
                    "filename": file.filename,
                    "processing_time_ms": round(processing_time, 2),
                },
            )
        )

        return DocumentUploadResponse(
            doc_id=doc_id,
            doc_classification=doc_classification,
            doc_department=doc_department,
            uploaded_by=user.email,
            processing_time_ms=round(processing_time, 2),
        )

    except Exception as e:
        # Log failed upload
        await audit.log(
            AuditLogEntry(
                user_id=user.user_id,
                user_email=user.email,
                ip_address=context.client_ip,
                event_category=EventCategory.MODIFICATION,
                event_type="document_upload",
                action=Action.WRITE,
                outcome=EventOutcome.FAILURE,
                resource_type=ResourceType.DOCUMENT,
                resource_name=file.filename,
                error_message=str(e),
            )
        )
        raise DocumentProcessingError(f"Failed to process document: {str(e)}") from e
