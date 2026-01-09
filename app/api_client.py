"""
Sentinel RAG - API Client Service

Professional API client for interacting with the FastAPI backend.
Implements proper error handling, retry logic, and type safety.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str, status_code: int = None, details: Dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class Classification(str, Enum):
    """Document classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class UserInfo:
    """User information model."""

    user_id: str
    email: str
    role: str
    department: str

    @classmethod
    def from_dict(cls, data: Dict) -> "UserInfo":
        return cls(
            user_id=data.get("user_id", ""),
            email=data.get("user_email", ""),
            role=data.get("user_role", ""),
            department=data.get("user_department", ""),
        )


@dataclass
class Document:
    """Document model."""

    doc_id: str
    title: str
    classification: str
    department: str
    chunk_count: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "Document":
        return cls(
            doc_id=data.get("doc_id", data.get("document_id", "")),
            title=data.get("title", data.get("doc_title", "Untitled")),
            classification=data.get(
                "classification", data.get("doc_classification", "")
            ),
            department=data.get("department", data.get("doc_department", "")),
            chunk_count=data.get("chunk_count"),
            created_at=data.get("created_at", data.get("upload_date")),
        )


@dataclass
class QueryResult:
    """Query result model."""

    content: str
    metadata: Dict[str, Any]

    @property
    def doc_id(self) -> Optional[str]:
        return self.metadata.get("doc_id")

    @property
    def chunk_id(self) -> Optional[str]:
        return self.metadata.get("chunk_id")

    @property
    def title(self) -> Optional[str]:
        return self.metadata.get("title")

    @property
    def classification(self) -> Optional[str]:
        return self.metadata.get("classification")

    @property
    def department(self) -> Optional[str]:
        return self.metadata.get("department")

    @classmethod
    def from_dict(cls, data: Dict) -> "QueryResult":
        return cls(
            content=data.get("page_content", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class HealthStatus:
    """Health check response model."""

    status: str
    version: str
    environment: str
    audit_enabled: bool
    components: Optional[Dict[str, Dict]] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "HealthStatus":
        return cls(
            status=data.get("status", "unknown"),
            version=data.get("version", ""),
            environment=data.get("environment", ""),
            audit_enabled=data.get("audit_enabled", False),
            components=data.get("components"),
        )


@dataclass
class UploadResult:
    """Document upload result model."""

    doc_id: str
    classification: str
    department: str
    uploaded_by: str
    processing_time_ms: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "UploadResult":
        return cls(
            doc_id=data.get("doc_id", ""),
            classification=data.get("doc_classification", ""),
            department=data.get("doc_department", ""),
            uploaded_by=data.get("uploaded_by", ""),
            processing_time_ms=data.get("processing_time_ms"),
        )


class SentinelRAGClient:
    """
    Professional API client for Sentinel RAG backend.

    Features:
    - Automatic retry with exponential backoff
    - Proper error handling with custom exceptions
    - Type-safe response models
    - Session management for connection pooling
    - Token-based authentication

    Usage:
        client = SentinelRAGClient("http://localhost:8000")
        client.set_token("your-jwt-token")
        user = client.get_current_user()
    """

    DEFAULT_TIMEOUT = 30  # seconds

    def __init__(
        self,
        base_url: str = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        """
        Initialize the API client.

        Args:
            base_url: API base URL (defaults to env var or localhost)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.timeout = timeout
        self._token: Optional[str] = None

        # Configure session with retry logic
        self._session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    @property
    def token(self) -> Optional[str]:
        """Get the current authentication token."""
        return self._token

    def set_token(self, token: str) -> None:
        """
        Set the authentication token.

        Args:
            token: JWT access token
        """
        self._token = token
        self._session.headers.update({"Authorization": f"Bearer {token}"})

    def clear_token(self) -> None:
        """Clear the authentication token."""
        self._token = None
        self._session.headers.pop("Authorization", None)

    @property
    def is_authenticated(self) -> bool:
        """Check if client has an authentication token set."""
        return self._token is not None

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        return urljoin(self.base_url.rstrip("/") + "/", endpoint.lstrip("/"))

    def _handle_response(self, response: requests.Response) -> Dict:
        """
        Handle API response with proper error handling.

        Args:
            response: requests.Response object

        Returns:
            Parsed JSON response

        Raises:
            APIError: If response indicates an error
        """
        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {"raw": response.text}

        if response.status_code >= 400:
            error_message = data.get(
                "detail", data.get("message", f"HTTP {response.status_code}")
            )
            raise APIError(
                message=str(error_message),
                status_code=response.status_code,
                details=data,
            )

        return data

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        files: Dict = None,
        params: Dict = None,
        **kwargs,
    ) -> Dict:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            files: Files to upload
            params: Query parameters
            **kwargs: Additional request arguments

        Returns:
            Parsed JSON response
        """
        url = self._build_url(endpoint)

        try:
            response = self._session.request(
                method=method,
                url=url,
                json=data if files is None else None,
                data=data if files is not None else None,
                files=files,
                params=params,
                timeout=self.timeout,
                **kwargs,
            )
            return self._handle_response(response)

        except requests.ConnectionError as e:
            raise APIError(
                message=f"Connection failed: Unable to reach {self.base_url}",
                details={"original_error": str(e)},
            )
        except requests.Timeout as e:
            raise APIError(
                message=f"Request timed out after {self.timeout} seconds",
                details={"original_error": str(e)},
            )

    # Health Endpoints
    # ----------------

    def health_check(self) -> HealthStatus:
        """
        Perform a basic health check.

        Returns:
            HealthStatus object
        """
        data = self._request("GET", "/health")
        return HealthStatus.from_dict(data)

    def readiness_check(self) -> HealthStatus:
        """
        Perform a detailed readiness check.

        Returns:
            HealthStatus object with component details
        """
        data = self._request("GET", "/health/ready")
        return HealthStatus.from_dict(data)

    def liveness_check(self) -> bool:
        """
        Perform a liveness check.

        Returns:
            True if API is alive
        """
        try:
            data = self._request("GET", "/health/live")
            return data.get("status") == "alive"
        except APIError:
            return False

    # Authentication Endpoints
    # ------------------------

    def get_login_url(self) -> str:
        """
        Get the OIDC login URL.

        Returns:
            Login URL for authentication
        """
        return self._build_url("/auth/login")

    def login_with_credentials(self, email: str, password: str) -> Tuple[str, UserInfo]:
        """
        Login with email and password (for demo/testing).

        Note: This is a mock endpoint for demo purposes.
        In production, use OIDC flow.

        Args:
            email: User email
            password: User password

        Returns:
            Tuple of (access_token, UserInfo)
        """
        data = self._request(
            "POST",
            "/auth/demo-login",
            data={
                "email": email,
                "password": password,
            },
        )

        token = data.get("access_token")
        if token:
            self.set_token(token)

        return token, UserInfo.from_dict(data.get("user", {}))

    def validate_token(self, token: str) -> bool:
        """
        Validate an access token.

        Args:
            token: JWT access token to validate

        Returns:
            True if token is valid
        """
        old_token = self._token
        try:
            self.set_token(token)
            self.get_current_user()
            return True
        except APIError:
            return False
        finally:
            if old_token:
                self.set_token(old_token)
            else:
                self.clear_token

    # User Endpoints
    # --------------

    def get_current_user(self) -> UserInfo:
        """
        Get current authenticated user information.

        Returns:
            UserInfo object

        Raises:
            APIError: If not authenticated or request fails
        """
        if not self.is_authenticated:
            raise APIError(
                "Not authenticated. Please set token first.", status_code=401
            )

        data = self._request("POST", "/api/user")
        return UserInfo.from_dict(data)

    def get_user_documents(self) -> List[Document]:
        """
        Get all documents uploaded by the current user.

        Returns:
            List of Document objects
        """
        if not self.is_authenticated:
            raise APIError(
                "Not authenticated. Please set token first.", status_code=401
            )

        data = self._request("POST", "/api/user/docs")
        return [Document.from_dict(doc) for doc in data]

    # Document Endpoints
    # ------------------

    def upload_document(
        self,
        file: Union[str, bytes],
        filename: str,
        title: str,
        description: str,
        department: str,
        classification: str,
    ) -> UploadResult:
        """
        Upload a document for processing.

        Args:
            file: File path or file content bytes
            filename: Name of the file
            title: Document title
            description: Document description
            department: Department identifier
            classification: Classification level

        Returns:
            UploadResult object
        """
        if not self.is_authenticated:
            raise APIError(
                "Not authenticated. Please set token first.", status_code=401
            )

        # Handle file input
        if isinstance(file, str):
            with open(file, "rb") as f:
                file_content = f.read()
        else:
            file_content = file

        files = {
            "file": (filename, file_content),
        }

        data = {
            "doc_title": title,
            "doc_description": description,
            "doc_department": department,
            "doc_classification": classification,
        }

        response = self._request(
            "POST", "/api/documents/upload", data=data, files=files
        )
        return UploadResult.from_dict(response)

    # Query Endpoints
    #

    def query(self, query_text: str, k: int = 5) -> List[QueryResult]:
        """
        Perform a RAG query.

        Args:
            query_text: Query string
            k: Number of results to return (default: 5)

        Returns:
            List of QueryResult objects
        """
        if not self.is_authenticated:
            raise APIError(
                "Not authenticated. Please set token first.", status_code=401
            )

        data = self._request(
            "POST",
            "/api/query",
            data={
                "user_query": query_text,
                "k": k,
            },
        )

        return [QueryResult.from_dict(result) for result in data]

    # Utility Methods
    # ---------------

    def get_classification_options(self) -> List[str]:
        """Get available classification options."""
        return [c.value for c in Classification]

    def get_department_options(self) -> List[str]:
        """
        Get available department options.

        Note: In production, this should be fetched from the API.
        """
        return [
            "engineering",
            "finance",
            "human_resources",
            "legal",
            "marketing",
            "operations",
            "sales",
        ]

    def close(self) -> None:
        """Close the API client session."""
        self._session.close()

    def __enter__(self) -> "SentinelRAGClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# Convenience function for quick client creation
def create_client(base_url: str = None, token: str = None) -> SentinelRAGClient:
    """
    Create a configured API client.

    Args:
        base_url: API base URL
        token: Optional JWT token

    Returns:
        Configured SentinelRAGClient
    """
    client = SentinelRAGClient(base_url=base_url)
    if token:
        client.set_token(token)
    return client
