"""
Testing utilities for Sentinel RAG.

This module provides:
- Centralized test user constants with predictable UUIDs
- Mock user context factory for creating test users
- Dependency mock helpers for FastAPI testing
- Test data builders and generators
- Common assertion helpers

Coverage:
- TestUsers: Constants for all test user types
- MockUserContext: Factory for creating mock UserContext instances
- create_mock_get_current_user: Dependency override helper
- TestDataBuilder: Builder pattern for complex test data
- AssertionHelpers: Common assertion patterns

Test types: Utility module (no tests, supports other test modules)
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sentinel_rag.services.auth import UserContext


#                        TEST DATA CONSTANTS
# ----------------------------------------------------------------------------


class TestUsers:
    """
    Centralized test user UUIDs for consistency across tests.

    Using predictable nil UUIDs for easy identification in test failures.
    Each UUID's last byte indicates the user type:
    - 001: Regular user (Engineering)
    - 002: HR user
    - 003: Finance user
    - 004: Admin user

    Usage:
        from tests.test_utils import TestUsers

        assert user.user_id == TestUsers.ADMIN_USER_ID
    """

    REGULAR_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
    HR_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
    FINANCE_USER_ID = UUID("00000000-0000-0000-0000-000000000003")
    ADMIN_USER_ID = UUID("00000000-0000-0000-0000-000000000004")

    # Additional test user IDs for multi-user scenarios
    MANAGER_USER_ID = UUID("00000000-0000-0000-0000-000000000005")
    INTERN_USER_ID = UUID("00000000-0000-0000-0000-000000000006")
    SECURITY_USER_ID = UUID("00000000-0000-0000-0000-000000000007")

    DEFAULT_TENANT_ID = "test-tenant-001"
    SECONDARY_TENANT_ID = "test-tenant-002"

    # Email patterns for different user types
    ADMIN_EMAIL = "admin@test.com"
    USER_EMAIL = "user@test.com"
    HR_EMAIL = "hr@test.com"
    FINANCE_EMAIL = "finance@test.com"


class TestDocuments:
    """
    Centralized test document constants for consistency.

    Provides predictable document IDs and metadata for testing.
    """

    DOC_ID_1 = UUID("10000000-0000-0000-0000-000000000001")
    DOC_ID_2 = UUID("10000000-0000-0000-0000-000000000002")
    DOC_ID_3 = UUID("10000000-0000-0000-0000-000000000003")

    CHUNK_ID_1 = UUID("20000000-0000-0000-0000-000000000001")
    CHUNK_ID_2 = UUID("20000000-0000-0000-0000-000000000002")
    CHUNK_ID_3 = UUID("20000000-0000-0000-0000-000000000003")


#                       MOCK USER CONTEXT FACTORY
# ----------------------------------------------------------------------------


class MockUserContext:
    """
    Factory for creating mock user contexts for testing.

    This class provides convenient methods to create UserContext instances
    with proper UUID types for testing different user roles and scenarios.

    All factory methods return valid UserContext instances that can be
    used directly in tests or with dependency overrides.

    Examples:
        # Create a predefined admin user
        admin = MockUserContext.create_admin()

        # Create a custom user for specific test cases
        specialist = MockUserContext.create_custom(
            user_id=uuid4(),
            email="specialist@company.com",
            tenant_id="tenant-123",
            role="Specialist",
            department="R&D"
        )
    """

    @staticmethod
    def create_admin(
        user_id: Optional[UUID] = None,
        email: str = TestUsers.ADMIN_EMAIL,
        tenant_id: str = TestUsers.DEFAULT_TENANT_ID,
        role: str = "Admin",
        department: str = "IT",
    ) -> UserContext:
        """
        Create a mock admin user context.

        Admin users have full access to all system resources.

        Args:
            user_id: UUID for the user (defaults to TestUsers.ADMIN_USER_ID)
            email: User email address
            tenant_id: Tenant identifier for multi-tenancy
            role: User role (defaults to "Admin")
            department: User department (defaults to "IT")

        Returns:
            UserContext: Admin user with full privileges
        """
        return UserContext(
            user_id=user_id or TestUsers.ADMIN_USER_ID,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    @staticmethod
    def create_user(
        user_id: Optional[UUID] = None,
        email: str = TestUsers.USER_EMAIL,
        tenant_id: str = TestUsers.DEFAULT_TENANT_ID,
        role: str = "User",
        department: str = "Engineering",
    ) -> UserContext:
        """
        Create a mock regular user context.

        Regular users have standard access to their own resources
        and department-level data.

        Args:
            user_id: UUID for the user (defaults to TestUsers.REGULAR_USER_ID)
            email: User email address
            tenant_id: Tenant identifier
            role: User role (defaults to "User")
            department: User department (defaults to "Engineering")

        Returns:
            UserContext: Regular user with standard privileges
        """
        return UserContext(
            user_id=user_id or TestUsers.REGULAR_USER_ID,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    @staticmethod
    def create_hr_user(
        user_id: Optional[UUID] = None,
        email: str = TestUsers.HR_EMAIL,
        tenant_id: str = TestUsers.DEFAULT_TENANT_ID,
        role: str = "Manager",
        department: str = "HR",
    ) -> UserContext:
        """
        Create a mock HR department user context.

        HR users have access to employee data and HR-specific documents.

        Args:
            user_id: UUID for the user (defaults to TestUsers.HR_USER_ID)
            email: User email address
            tenant_id: Tenant identifier
            role: User role (defaults to "Manager")
            department: User department (defaults to "HR")

        Returns:
            UserContext: HR Manager with HR department access
        """
        return UserContext(
            user_id=user_id or TestUsers.HR_USER_ID,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    @staticmethod
    def create_finance_user(
        user_id: Optional[UUID] = None,
        email: str = TestUsers.FINANCE_EMAIL,
        tenant_id: str = TestUsers.DEFAULT_TENANT_ID,
        role: str = "Analyst",
        department: str = "Finance",
    ) -> UserContext:
        """
        Create a mock Finance department user context.

        Finance users have access to financial data and budget documents.

        Args:
            user_id: UUID for the user (defaults to TestUsers.FINANCE_USER_ID)
            email: User email address
            tenant_id: Tenant identifier
            role: User role (defaults to "Analyst")
            department: User department (defaults to "Finance")

        Returns:
            UserContext: Finance Analyst with Finance department access
        """
        return UserContext(
            user_id=user_id or TestUsers.FINANCE_USER_ID,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    @staticmethod
    def create_custom(
        user_id: Union[UUID, str],
        email: str,
        tenant_id: str,
        role: str,
        department: str,
    ) -> UserContext:
        """
        Create a custom mock user context with specified parameters.

        Use this when you need a user with specific attributes not covered
        by the predefined factory methods.

        Args:
            user_id: UUID for the user (required, can be string or UUID)
            email: User email address (required)
            tenant_id: Tenant identifier (required)
            role: User role (required)
            department: User department (required)

        Returns:
            UserContext: Custom configured user

        Example:
            security_analyst = MockUserContext.create_custom(
                user_id=uuid4(),
                email="security@company.com",
                tenant_id="tenant-secure",
                role="Security Analyst",
                department="Security"
            )
        """
        # Handle string UUID conversion
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        return UserContext(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    @staticmethod
    def create_from_different_tenant(
        base_role: str = "User",
        tenant_id: str = TestUsers.SECONDARY_TENANT_ID,
    ) -> UserContext:
        """
        Create a user from a different tenant for isolation tests.

        Args:
            base_role: User role
            tenant_id: Different tenant ID

        Returns:
            UserContext: User from a different tenant
        """
        return UserContext(
            user_id=uuid4(),
            email=f"user-{uuid4().hex[:8]}@tenant2.com",
            tenant_id=tenant_id,
            role=base_role,
            department="Engineering",
        )


#                       DEPENDENCY MOCK HELPERS
# ----------------------------------------------------------------------------


def create_mock_get_current_user(user_context: UserContext):
    """
    Create a mock dependency function that returns the specified user context.

    This function is used with FastAPI's dependency_overrides to bypass
    OIDC authentication during testing.

    Args:
        user_context: The UserContext to return when dependency is called

    Returns:
        Async function that returns the user context

    Example:
        from sentinel_rag.api.dependencies import get_current_active_user

        mock_user = MockUserContext.create_admin()
        app.dependency_overrides[get_current_active_user] = (
            create_mock_get_current_user(mock_user)
        )

        # Now all requests will be authenticated as the mock admin
        response = client.post("/api/user")
        assert response.json()["user_role"] == "Admin"
    """

    async def mock_get_current_user() -> UserContext:
        """Mock dependency that returns the configured user context."""
        return user_context

    return mock_get_current_user


def create_mock_failing_auth(
    status_code: int = 401,
    detail: str = "Not authenticated",
):
    """
    Create a mock auth dependency that always raises an HTTPException.

    Useful for testing error handling when authentication fails.

    Args:
        status_code: HTTP status code to raise
        detail: Error message detail

    Returns:
        Async function that raises HTTPException
    """
    from fastapi import HTTPException

    async def mock_failing_auth() -> UserContext:
        raise HTTPException(status_code=status_code, detail=detail)

    return mock_failing_auth


#                       TEST DATA BUILDERS
# ----------------------------------------------------------------------------


class QueryRequestBuilder:
    """
    Builder pattern for creating query request test data.

    Allows fluent construction of query requests with various configurations.

    Example:
        request = (QueryRequestBuilder()
            .with_query("What is the vacation policy?")
            .build())
    """

    def __init__(self):
        self._query = "Test query"

    def with_query(self, query: str) -> "QueryRequestBuilder":
        """Set the query text."""
        self._query = query
        return self

    def with_empty_query(self) -> "QueryRequestBuilder":
        """Set an empty query for validation testing."""
        self._query = ""
        return self

    def with_long_query(self, length: int = 5001) -> "QueryRequestBuilder":
        """Create a query exceeding max length."""
        self._query = "a" * length
        return self

    def with_whitespace_query(self) -> "QueryRequestBuilder":
        """Create a query with leading/trailing whitespace."""
        self._query = "  test query with whitespace  "
        return self

    def with_special_characters(self) -> "QueryRequestBuilder":
        """Create a query with special characters."""
        self._query = "What about <script>alert('xss')</script>?"
        return self

    def with_unicode(self) -> "QueryRequestBuilder":
        """Create a query with unicode characters."""
        self._query = "¿Cuál es la política de vacaciones? 日本語テスト"
        return self

    def build(self) -> Dict[str, Any]:
        """Build the query request dictionary."""
        return {"user_query": self._query}


class DocumentUploadBuilder:
    """
    Builder pattern for creating document upload test data.

    Example:
        upload = (DocumentUploadBuilder()
            .with_title("HR Policy")
            .with_department("HR")
            .with_classification("Confidential")
            .build())
    """

    def __init__(self):
        self._title = "Test Document"
        self._description = "Test document description"
        self._department = "Engineering"
        self._classification = "Internal"

    def with_title(self, title: str) -> "DocumentUploadBuilder":
        """Set document title."""
        self._title = title
        return self

    def with_description(self, description: str) -> "DocumentUploadBuilder":
        """Set document description."""
        self._description = description
        return self

    def with_department(self, department: str) -> "DocumentUploadBuilder":
        """Set document department."""
        self._department = department
        return self

    def with_classification(self, classification: str) -> "DocumentUploadBuilder":
        """Set document classification level."""
        self._classification = classification
        return self

    def with_long_title(self, length: int = 200) -> "DocumentUploadBuilder":
        """Create a document with a very long title."""
        self._title = "A" * length
        return self

    def with_long_description(self, length: int = 500) -> "DocumentUploadBuilder":
        """Create a document with a very long description."""
        self._description = "B" * length
        return self

    def build(self) -> Dict[str, str]:
        """Build the upload form data dictionary."""
        return {
            "doc_title": self._title,
            "doc_description": self._description,
            "doc_department": self._department,
            "doc_classification": self._classification,
        }


class DocumentResponseBuilder:
    """
    Builder for creating mock document response data.
    """

    def __init__(self):
        self._page_content = "Sample document content"
        self._metadata = {
            "doc_id": str(TestDocuments.DOC_ID_1),
            "chunk_id": str(TestDocuments.CHUNK_ID_1),
            "title": "Test Document",
            "department": "Engineering",
            "classification": "Internal",
        }

    def with_content(self, content: str) -> "DocumentResponseBuilder":
        """Set page content."""
        self._page_content = content
        return self

    def with_pii_content(self) -> "DocumentResponseBuilder":
        """Add PII markers to content."""
        self._page_content = "Contact <EMAIL> or <PHONE> for details"
        return self

    def with_metadata(self, **kwargs) -> "DocumentResponseBuilder":
        """Update metadata fields."""
        self._metadata.update(kwargs)
        return self

    def build(self) -> Dict[str, Any]:
        """Build the document response dictionary."""
        return {
            "page_content": self._page_content,
            "metadata": self._metadata.copy(),
        }


#                       ASSERTION HELPERS
# ----------------------------------------------------------------------------


class AssertionHelpers:
    """
    Common assertion patterns for Sentinel RAG tests.

    Provides reusable assertion methods with descriptive failure messages.
    """

    @staticmethod
    def assert_user_response_valid(
        response_data: Dict[str, Any],
        expected_email: Optional[str] = None,
        expected_role: Optional[str] = None,
        expected_department: Optional[str] = None,
    ) -> None:
        """
        Assert that a user response contains all required fields.

        Args:
            response_data: Response JSON data
            expected_email: Expected email (optional)
            expected_role: Expected role (optional)
            expected_department: Expected department (optional)
        """
        required_fields = ["user_id", "user_email", "user_role", "user_department"]

        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"
            assert response_data[field] is not None, f"Field {field} is None"

        if expected_email:
            assert response_data["user_email"] == expected_email
        if expected_role:
            assert response_data["user_role"] == expected_role
        if expected_department:
            assert response_data["user_department"] == expected_department

        # Validate email format
        assert "@" in response_data["user_email"], "Invalid email format"

    @staticmethod
    def assert_document_response_valid(response_data: Dict[str, Any]) -> None:
        """
        Assert that a document response has the correct structure.

        Args:
            response_data: Response JSON data
        """
        assert "page_content" in response_data, "Missing 'page_content' field"
        assert "metadata" in response_data, "Missing 'metadata' field"
        assert isinstance(response_data["page_content"], str)
        assert isinstance(response_data["metadata"], dict)

    @staticmethod
    def assert_error_response_valid(
        response_data: Dict[str, Any],
        expected_error: Optional[str] = None,
    ) -> None:
        """
        Assert that an error response has the correct structure.

        Args:
            response_data: Response JSON data
            expected_error: Expected error code (optional)
        """
        assert "error" in response_data or "message" in response_data
        if expected_error and "error" in response_data:
            assert response_data["error"] == expected_error

    @staticmethod
    def assert_query_results_valid(results: List[Dict[str, Any]]) -> None:
        """
        Assert that query results have the correct structure.

        Args:
            results: List of document responses
        """
        assert isinstance(results, list), "Query results must be a list"
        for item in results:
            assert "page_content" in item
            assert "metadata" in item


#                       FILE CONTENT GENERATORS
# ----------------------------------------------------------------------------


def generate_test_file_content(
    content_type: str = "text",
    size_bytes: int = 100,
) -> bytes:
    """
    Generate test file content of various types.

    Args:
        content_type: Type of content ("text", "pdf", "markdown", "empty")
        size_bytes: Approximate size of content

    Returns:
        bytes: File content
    """
    if content_type == "empty":
        return b""
    elif content_type == "pdf":
        # Fake PDF header for testing
        return b"%PDF-1.4\n" + b"x" * (size_bytes - 10)
    elif content_type == "markdown":
        return b"# Test Document\n\nThis is a test markdown file.\n" + b"x" * (
            size_bytes - 50
        )
    else:
        return b"Test document content. " * (size_bytes // 22 + 1)


def generate_random_uuid() -> UUID:
    """Generate a random UUID for testing."""
    return uuid4()


def generate_timestamp() -> datetime:
    """Generate a current UTC timestamp."""
    return datetime.now(timezone.utc)


#                       MOCK RESPONSE FACTORIES
# ----------------------------------------------------------------------------


class MockResponseFactory:
    """
    Factory for creating mock API responses for testing.
    """

    @staticmethod
    def upload_success(
        doc_id: Optional[UUID] = None,
        department: str = "Engineering",
        classification: str = "Internal",
        uploaded_by: str = TestUsers.USER_EMAIL,
    ) -> Dict[str, Any]:
        """Create a successful document upload response."""
        return {
            "doc_id": str(doc_id or TestDocuments.DOC_ID_1),
            "doc_classification": classification,
            "doc_department": department,
            "uploaded_by": uploaded_by,
            "processing_time_ms": 150.5,
        }

    @staticmethod
    def query_results(count: int = 3) -> List[Dict[str, Any]]:
        """Create mock query results."""
        results = []
        for i in range(count):
            results.append(
                {
                    "page_content": f"Document content {i + 1}",
                    "metadata": {
                        "doc_id": str(uuid4()),
                        "chunk_id": str(uuid4()),
                        "title": f"Document {i + 1}",
                        "department": "Engineering",
                        "classification": "Internal",
                    },
                }
            )
        return results

    @staticmethod
    def health_response(
        status: str = "healthy",
        version: str = "1.0.0-test",
        environment: str = "testing",
    ) -> Dict[str, Any]:
        """Create a health check response."""
        return {
            "status": status,
            "version": version,
            "environment": environment,
            "audit_enabled": False,
            "timestamp": generate_timestamp().isoformat(),
        }


"""
Coverage Summary:
- TestUsers: 7 user IDs, 2 tenant IDs, 4 email patterns
- TestDocuments: 3 document IDs, 3 chunk IDs
- MockUserContext: 6 factory methods (admin, user, HR, finance, custom, different_tenant)
- Dependency helpers: 2 functions (success, failure)
- Builders: 3 (QueryRequest, DocumentUpload, DocumentResponse)
- AssertionHelpers: 4 methods
- File generators: 3 functions
- MockResponseFactory: 3 methods

Total utility functions: 25+
Coverage: 100% of test utility needs
"""
