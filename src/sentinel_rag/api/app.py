import os
from fastapi import FastAPI, UploadFile, HTTPException, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from sentinel_rag import DatabaseManager
from sentinel_rag import SentinelEngine


# Load file path from .env
config = os.getenv("SENTINEL_CONFIG_PATH")

# Initialize Engine and Database
db = DatabaseManager()
engine = SentinelEngine(db=db, config_file=config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Sentinel RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- Pydantic Models ---


class UserLoginRequest(BaseModel):
    user_email: str


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
    user_email: str
    k: int = 5


class DocumentResponse(BaseModel):
    page_content: str
    metadata: Dict[str, Any]


# --- Endpoints ---

# ---- User Endpoints ----


@app.post("/user", response_model=UserResponse)
async def get_user(request: UserLoginRequest):
    user = db.get_user_by_email(request.user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        user_id=str(user["user_id"]),
        user_email=user["email"],
        full_name=user["full_name"],
        user_role="sample_role",
        user_department="sample_department",
    )


@app.post("/user/login", response_model=UserResponse)
async def login_user(request: UserLoginRequest):
    user = db.get_user_by_email(request.user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        user_id=str(user["user_id"]),
        user_email=user["email"],
        full_name=user["full_name"],
        user_role="sample_role",
        user_department="sample_department",
    )


@app.post("/user/create", response_model=UserResponse)
async def create_user(request: UserCreateRequest):
    try:
        # Check if user already exists to avoid error or handle gracefully
        existing_user = db.get_user_by_email(request.user_email)
        if existing_user:
            return UserResponse(
                user_id=str(existing_user["user_id"]),
                user_email=existing_user["email"],
                full_name=existing_user["full_name"],
                user_role="sample_role",
                user_department="sample_department",
            )

        # Check if role exists in department
        available_roles = db.get_roles_by_department(request.user_department)
        if not available_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Department '{request.user_department}' not found or has no roles",
            )

        if request.role not in available_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Role '{request.user_role}' not found in department '{request.user_department}'",
            )

        uid = db.create_user(request.user_email, request.full_name)
        db.assign_role(uid, request.user_role, request.user_department)
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
async def get_user_uploaded_documents(request: UserLoginRequest):
    user = db.get_user_by_email(request.user_email)

    if not user:
        raise HTTPException(status_code=500, detail="User not found")
    user_id = str(user["user_id"])

    try:
        documents = db.get_document_uploads_by_user(user_id=user_id)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Document Endpoints ----


@app.post("/upload", response_model=DocUploadResponse)
async def upload_documents(
    file: UploadFile = File(...),
    doc_title: str = Form(...),
    doc_description: str = Form(...),
    user_email: str = Form(...),
    doc_department: str = Form(...),
    doc_classification: str = Form(...),
):
    # 1. Get User ID
    user = db.get_user_by_email(user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user["user_id"])

    # 2. Get Department ID
    department_id = db.get_department_id_by_name(doc_department)
    if not department_id:
        raise HTTPException(
            status_code=400, detail=f"Department '{doc_department}' not found"
        )
    try:
        # 3. Ingest
        doc_id = engine.ingest_documents(
            source=file,
            title=doc_title,
            description=doc_description,
            user_id=user_id,
            department_id=department_id,
            classification=doc_classification,
        )
        return DocUploadResponse(
            doc_id=doc_id,
            doc_classification=doc_classification,
            doc_department=doc_department,
            uploaded_by=user_email,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Query Endpoint ----


@app.post("/query", response_model=List[DocumentResponse])
async def query_documents(request: QueryRequest):
    # 1. Get User ID
    user = db.get_user_by_email(request.user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user["user_id"])

    try:
        results = engine.query(request.user_query, user_id=user_id, k=request.k)
        return [
            DocumentResponse(page_content=doc.page_content, metadata=doc.metadata)
            for doc in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Health Check Endpoint ----


@app.get("/")
async def root():
    return {"message": "Welcome to Sentinel RAG API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
