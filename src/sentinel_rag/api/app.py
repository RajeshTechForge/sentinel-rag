import os
from datetime import datetime
import asyncpg
from fastapi import FastAPI, UploadFile, HTTPException, Request, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from sentinel_rag import DatabaseManager
from sentinel_rag import SentinelEngine

from sentinel_rag import AuditLoggingMiddleware
from sentinel_rag import (
    AuditService,
    AuditLogEntry,
    QueryAuditEntry,
    AuthAuditEntry,
    EventCategory,
    EventOutcome,
    Action,
    ResourceType,
    extract_client_info,
)


# Load file path from .env
config = os.getenv("SENTINEL_CONFIG_PATH")


# --- Configuration ---
# Set this to False to disable audit logging
ENABLE_AUDIT_LOGGING = True


class MockAuditService:
    """No-op audit service for when logging is disabled"""

    async def log(self, entry):
        return "mock_log_id"

    async def log_auth(self, log_id, entry):
        pass

    async def log_query(self, log_id, entry):
        pass


# Global variables
db = None
engine = None
audit_service = None
audit_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, engine, audit_service, audit_pool

    # Initialize Engine and Database
    db = DatabaseManager()
    engine = SentinelEngine(db=db, config_file=config)

    if ENABLE_AUDIT_LOGGING:
        # Initialize Audit Service (separate async connection pool)
        audit_pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "sample_db"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            min_size=5,
            max_size=10,
        )
        audit_service = AuditService(audit_pool)
        print("✅ Audit logging initialized")
    else:
        audit_service = MockAuditService()
        print("⚠️ Audit logging disabled")

    yield

    # Cleanup
    if engine:
        engine.close()
    if audit_pool:
        await audit_pool.close()


app = FastAPI(title="Sentinel RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Add Audit Middleware
if ENABLE_AUDIT_LOGGING:
    app.add_middleware(AuditLoggingMiddleware, audit_service=lambda: audit_service)


# --- Pydantic Models ---


class UserLoginRequest(BaseModel):
    user_email: str
    user_id: str = None  # Optional for backward compatibility


class UserCreateRequest(BaseModel):
    user_email: str
    full_name: str
    user_role: str
    user_department: str


class UserResponse(BaseModel):
    user_id: str
    user_email: str
    full_name: str
    user_role: str
    user_department: str


class DocUploadResponse(BaseModel):
    doc_id: str
    doc_classification: str
    doc_department: str
    uploaded_by: str


class QueryRequest(BaseModel):
    user_query: str
    user_id: str = None
    user_email: str
    k: int = 5


class DocumentResponse(BaseModel):
    page_content: str
    metadata: Dict[str, Any]


# --- Helper Functions ---


async def get_audit_service():
    """Dependency to inject audit service"""
    return audit_service


def store_user_in_request(request: Request, user_id: str, user_email: str):
    """Store user info in request state for audit middleware"""
    request.state.user_id = user_id
    request.state.user_email = user_email


# --- Endpoints ---

# ---- User Endpoints ----


@app.post("/user", response_model=UserResponse)
async def get_user(request: UserLoginRequest, req: Request):
    user = db.get_user_by_email(request.user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_info = db.get_user_role_and_department(str(user["user_id"]))
    user_department, user_role = user_info[0]
    store_user_in_request(req, str(user["user_id"]), user["email"])

    return UserResponse(
        user_id=str(user["user_id"]),
        user_email=user["email"],
        full_name=user["full_name"],
        user_role=user_role,
        user_department=user_department,
    )


@app.post("/user/login", response_model=UserResponse)
async def login_user(request: UserLoginRequest, req: Request):
    client_info = extract_client_info(req)
    user = db.get_user_by_email(request.user_email)

    if not user:
        # Log failed login
        main_entry = AuditLogEntry(
            user_email=request.user_email,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            event_category=EventCategory.AUTHENTICATION,
            event_type="login_failure",
            action=Action.LOGIN,
            outcome=EventOutcome.FAILURE,
            error_message="User not found",
        )
        log_id = await audit_service.log(main_entry)

        auth_entry = AuthAuditEntry(
            email=request.user_email,
            auth_method="email_only",
            event_type="login_failure",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            failed_attempts_count=1,
        )
        await audit_service.log_auth(log_id, auth_entry)

        raise HTTPException(status_code=404, detail="User not found")

    user_info = db.get_user_role_and_department(str(user["user_id"]))
    user_department, user_role = user_info[0]
    store_user_in_request(req, str(user["user_id"]), user["email"])

    # Log successful login
    main_entry = AuditLogEntry(
        user_id=user["user_id"],
        user_email=user["email"],
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        session_id=client_info["session_id"],
        event_category=EventCategory.AUTHENTICATION,
        event_type="login_success",
        action=Action.LOGIN,
        outcome=EventOutcome.SUCCESS,
    )
    log_id = await audit_service.log(main_entry)

    auth_entry = AuthAuditEntry(
        user_id=user["user_id"],
        email=user["email"],
        auth_method="email_only",
        event_type="login_success",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
    )
    await audit_service.log_auth(log_id, auth_entry)

    return UserResponse(
        user_id=str(user["user_id"]),
        user_email=user["email"],
        full_name=user["full_name"],
        user_role=user_role,
        user_department=user_department,
    )


@app.post("/user/create", response_model=UserResponse)
async def create_user(request: UserCreateRequest, req: Request):
    client_info = extract_client_info(req)

    try:
        # Check if user already exists to avoid error or handle gracefully
        existing_user = db.get_user_by_email(request.user_email)
        user_info = db.get_user_role_and_department(str(existing_user["user_id"]))
        user_department, user_role = user_info[0]
        if existing_user:
            return UserResponse(
                user_id=str(existing_user["user_id"]),
                user_email=existing_user["email"],
                full_name=existing_user["full_name"],
                user_role=user_role,
                user_department=user_department,
            )

        # Check if role exists in department
        available_roles = db.get_roles_by_department(request.user_department)
        if not available_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Department '{request.user_department}' not found or has no roles",
            )

        if request.user_role not in available_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Role '{request.user_role}' not found in department '{request.user_department}'",
            )

        uid = db.create_user(request.user_email, request.full_name)
        db.assign_role(uid, request.user_role, request.user_department)

        # Store in request state
        store_user_in_request(req, uid, request.user_email)

        # Log user creation
        main_entry = AuditLogEntry(
            user_email=request.user_email,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            event_category=EventCategory.ADMIN,
            event_type="user_creation",
            action=Action.WRITE,
            outcome=EventOutcome.SUCCESS,
            resource_type=ResourceType.USER,
            resource_id=uid,
            resource_name=request.user_email,
            department_name=request.user_department,
            role_name=request.user_role,
            metadata={
                "full_name": request.full_name,
                "department": request.user_department,
                "role": request.user_role,
            },
        )
        await audit_service.log(main_entry)

        return UserResponse(
            user_id=uid,
            user_email=request.user_email,
            full_name=request.full_name,
            user_role=request.user_role,
            user_department=request.user_department,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/docs", response_model=List[Dict])
async def get_user_uploaded_documents(request: UserLoginRequest, req: Request):
    user = db.get_user_by_email(request.user_email)

    if not user:
        raise HTTPException(status_code=500, detail="User not found")

    user_id = str(user["user_id"])
    store_user_in_request(req, user_id, user["email"])

    try:
        documents = db.get_document_uploads_by_user(user_id=user_id)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Document Endpoints ----


@app.post("/upload", response_model=DocUploadResponse)
async def upload_documents(
    req: Request,
    file: UploadFile = File(...),
    doc_title: str = Form(...),
    doc_description: str = Form(...),
    user_email: str = Form(...),
    doc_department: str = Form(...),
    doc_classification: str = Form(...),
):
    client_info = extract_client_info(req)

    # 1. Get User ID
    user = db.get_user_by_email(user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user["user_id"])

    store_user_in_request(req, user_id, user_email)

    # 2. Get Department ID
    department_id = db.get_department_id_by_name(doc_department)
    if not department_id:
        raise HTTPException(
            status_code=400, detail=f"Department '{doc_department}' not found"
        )
    try:
        start_time = datetime.now()

        # 3. Ingest
        doc_id = engine.ingest_documents(
            source=file,
            title=doc_title,
            description=doc_description,
            user_id=user_id,
            department_id=department_id,
            classification=doc_classification,
        )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # 4. Log document upload
        main_entry = AuditLogEntry(
            user_id=user_id,
            user_email=user_email,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            session_id=client_info["session_id"],
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
        await audit_service.log(main_entry)

        return DocUploadResponse(
            doc_id=doc_id,
            doc_classification=doc_classification,
            doc_department=doc_department,
            uploaded_by=user_email,
        )
    except Exception as e:
        # Log failed upload
        main_entry = AuditLogEntry(
            user_id=user_id,
            user_email=user_email,
            ip_address=client_info["ip_address"],
            event_category=EventCategory.MODIFICATION,
            event_type="document_upload",
            action=Action.WRITE,
            outcome=EventOutcome.FAILURE,
            resource_type=ResourceType.DOCUMENT,
            resource_name=file.filename,
            error_message=str(e),
        )
        await audit_service.log(main_entry)

        raise HTTPException(status_code=500, detail=str(e))


# ---- Query Endpoint ----


@app.post("/query", response_model=List[DocumentResponse])
async def query_documents(request: QueryRequest, req: Request):
    client_info = extract_client_info(req)
    start_time = datetime.now()

    store_user_in_request(req, request.user_id, request.user_email)

    # 1. Verify user exists
    user = db.get_user_by_email(request.user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user["user_id"])

    try:
        # 2. Perform RAG query
        vector_search_start = datetime.now()
        results = engine.query(request.user_query, user_id=user_id, k=request.k)
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        vector_time = (datetime.now() - vector_search_start).total_seconds() * 1000

        # 3. if PII was detected
        pii_detected = False
        pii_types_found = []

        for doc in results:
            content = doc.page_content
            if "<" in content and ">" in content:
                pii_detected = True
                # Extract PII types
                import re

                pii_matches = re.findall(r"<([A-Z_]+)>", content)
                pii_types_found.extend(pii_matches)

        pii_types_found = list(set(pii_types_found))

        # 4. Extract document IDs and chunk IDs
        docs_accessed = list(
            set(
                [
                    doc.metadata.get("doc_id")
                    for doc in results
                    if doc.metadata.get("doc_id")
                ]
            )
        )

        chunks_accessed = list(
            set(
                [
                    doc.metadata.get("chunk_id")
                    for doc in results
                    if doc.metadata.get("chunk_id")
                ]
            )
        )

        # 5. Log main audit entry
        main_entry = AuditLogEntry(
            user_id=user_id,
            user_email=request.user_email,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            session_id=client_info["session_id"],
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
                "k_requested": request.k,
                "total_time_ms": round(total_time, 2),
            },
        )
        log_id = await audit_service.log(main_entry)

        # 6. Log query-specific audit
        query_entry = QueryAuditEntry(
            user_id=user_id,
            query_text=request.user_query,
            chunks_retrieved=len(results),
            chunks_accessed=chunks_accessed,
            documents_accessed=docs_accessed,
            vector_search_time_ms=round(vector_time, 2),
            llm_processing_time_ms=0.0,  # don't have LLM yet
            total_response_time_ms=round(total_time, 2),
            filters_applied={"user_id": user_id, "k": request.k},
            chunks_filtered=0,
        )
        await audit_service.log_query(log_id, query_entry)

        # 7. Return results
        return [
            DocumentResponse(page_content=doc.page_content, metadata=doc.metadata)
            for doc in results
        ]

    except Exception as e:
        # Log failed query
        main_entry = AuditLogEntry(
            user_id=user_id,
            user_email=request.user_email,
            ip_address=client_info["ip_address"],
            event_category=EventCategory.DATA_ACCESS,
            event_type="rag_query",
            action=Action.READ,
            outcome=EventOutcome.FAILURE,
            query_text=request.user_query[:500],
            error_message=str(e),
        )
        await audit_service.log(main_entry)

        raise HTTPException(status_code=500, detail=str(e))


# ---- Health Check Endpoint ----


@app.get("/")
async def root():
    return {"message": "Welcome to Sentinel RAG API"}


@app.get("/health")
async def health():
    return {"status": "healthy", "audit_enabled": ENABLE_AUDIT_LOGGING}
