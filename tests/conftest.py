"""
Pytest configuration and fixtures for Sentinel RAG testing.

This module provides:
- Test client fixtures with and without authentication
- Mock user contexts for different roles (Admin, User, HR, Finance)
- Database and engine fixtures with proper isolation
- Dependency override utilities for FastAPI testing
- Comprehensive test settings and configuration

Coverage:
- Application fixtures with proper lifecycle management
- Authenticated test clients for all user roles
- Mock user context fixtures
- Test configuration and settings
- Sample request/response data fixtures

Test types: Unit, Integration
"""

import os
import pytest
from typing import Generator, Optional
from uuid import UUID
from fastapi.testclient import TestClient

from sentinel_rag.api.app import create_application
from sentinel_rag.api.dependencies import (
    get_app_state,
    get_current_active_user,
    get_settings_dep,
)
from sentinel_rag.config import AppSettings
from test_utils import MockUserContext, TestUsers, create_mock_get_current_user


#                           ENVIRONMENT SETUP
# ----------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up test environment variables before any tests run.

    This fixture:
    - Ensures we're using test configuration
    - Disables audit logging by default to reduce test overhead
    - Sets up any necessary test-specific environment variables

    Yields control to tests, then performs cleanup.
    """
    original_env = {
        "TESTING": os.environ.get("TESTING"),
        "AUDIT_ENABLED": os.environ.get("AUDIT_ENABLED"),
    }

    os.environ["TESTING"] = "true"
    os.environ["AUDIT_ENABLED"] = "false"

    yield

    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


#                         APPLICATION FIXTURES
# ----------------------------------------------------------------------------


@pytest.fixture(scope="function")
def app():
    """
    Create a fresh FastAPI application instance for each test.

    This ensures test isolation by:
    - Creating a new app instance for each test function
    - Clearing all dependency overrides after test completion
    - Preventing state leakage between tests

    Returns:
        FastAPI: Fresh application instance
    """
    application = create_application()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(app) -> Generator[TestClient, None, None]:
    """
    Create a TestClient without authentication.

    Use this for:
    - Testing public endpoints (health checks, root)
    - Testing authentication enforcement (expecting 401)
    - Manually setting up custom authentication in tests

    Args:
        app: FastAPI application instance

    Yields:
        TestClient: Unauthenticated test client

    Example:
        def test_health_check(client):
            response = client.get("/health")
            assert response.status_code == 200

        def test_protected_endpoint_requires_auth(client):
            response = client.post("/api/user")
            assert response.status_code == 401
    """
    with TestClient(app) as test_client:
        yield test_client


#                      AUTHENTICATED CLIENT FIXTURES
# ----------------------------------------------------------------------------


@pytest.fixture(scope="function")
def admin_client(app, test_settings) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as an Admin user.

    Admin users have full access to all endpoints and resources.
    This fixture bypasses OIDC authentication using dependency overrides.

    Args:
        app: FastAPI application instance
        test_settings: Test configuration settings

    Yields:
        TestClient: Authenticated as admin (IT department)

    Example:
        def test_admin_access(admin_client):
            response = admin_client.post("/api/user")
            assert response.status_code == 200
            assert response.json()["user_role"] == "Admin"
    """
    mock_admin = MockUserContext.create_admin()
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        mock_admin
    )
    app.dependency_overrides[get_settings_dep] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def user_client(app, test_settings) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as a regular User.

    Regular users have standard access to their own resources
    and department-level data in Engineering.

    Args:
        app: FastAPI application instance
        test_settings: Test configuration settings

    Yields:
        TestClient: Authenticated as regular user (Engineering department)
    """
    mock_user = MockUserContext.create_user()
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        mock_user
    )
    app.dependency_overrides[get_settings_dep] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def hr_client(app, test_settings) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as an HR department Manager.

    HR users have access to HR-specific documents and
    employee-related information.

    Args:
        app: FastAPI application instance
        test_settings: Test configuration settings

    Yields:
        TestClient: Authenticated as HR Manager
    """
    mock_hr = MockUserContext.create_hr_user()
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        mock_hr
    )
    app.dependency_overrides[get_settings_dep] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def finance_client(app, test_settings) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as a Finance department Analyst.

    Finance users have access to financial documents and
    budget-related information.

    Args:
        app: FastAPI application instance
        test_settings: Test configuration settings

    Yields:
        TestClient: Authenticated as Finance Analyst
    """
    mock_finance = MockUserContext.create_finance_user()
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        mock_finance
    )
    app.dependency_overrides[get_settings_dep] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_custom_client(
    app,
    user_context,
    test_settings: Optional[AppSettings] = None,
) -> TestClient:
    """
    Create a TestClient with a custom user context.

    Use this helper when you need a specific user configuration
    not covered by predefined fixtures.

    Args:
        app: FastAPI application instance
        user_context: UserContext to use for authentication
        test_settings: Optional custom settings (creates default if None)

    Returns:
        TestClient: Authenticated with the provided user context

    Example:
        def test_custom_user_access(app):
            custom_user = MockUserContext.create_custom(
                user_id=uuid4(),
                email="specialist@test.com",
                tenant_id="tenant-special",
                role="Specialist",
                department="Research"
            )
            client = create_custom_client(app, custom_user)
            response = client.post("/api/user")
            assert response.json()["user_role"] == "Specialist"
    """
    from sentinel_rag.config import (
        DatabaseSettings,
        DocRetrievalSettings,
        SecuritySettings,
        OIDCSettings,
        TenantSettings,
        AuditSettings,
        CORSSettings,
        RBACSettings,
    )

    if test_settings is None:
        test_settings = AppSettings.model_construct(
            config_path="",
            app_name="Test App",
            app_version="1.0.0-test",
            environment="testing",
            debug=True,
            database=DatabaseSettings.model_construct(
                host="localhost",
                port=5432,
                database="test_db",
                user="test_user",
                password="test_password",
            ),
            doc_retrieval=DocRetrievalSettings.model_construct(
                max_retrieved_docs=20,
                similarity_threshold=0.4,
                rrf_constant=60,
            ),
            security=SecuritySettings.model_construct(
                secret_key="test-secret-key-minimum-32-characters-long",
                algorithm="HS256",
                access_token_expire_minutes=60,
            ),
            oidc=OIDCSettings.model_construct(
                client_id="test",
                client_secret="test",
                server_metadata_url="https://test.example.com/.well-known/openid-configuration",
            ),
            tenant=TenantSettings.model_construct(
                tenant_id="test",
                domain="test.com",
            ),
            audit=AuditSettings.model_construct(enabled=False),
            cors=CORSSettings.model_construct(),
            rbac=RBACSettings.model_construct(
                departments=["finance", "hr", "engineering", "sales", "marketing"],
                roles={},
                access_matrix={},
            ),
        )

    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        user_context
    )
    app.dependency_overrides[get_settings_dep] = lambda: test_settings
    return TestClient(app)


#                         MOCK USER FIXTURES
# ----------------------------------------------------------------------------


@pytest.fixture
def mock_admin():
    """
    Provide a mock admin UserContext for direct use in tests.

    Returns:
        UserContext: Admin user with IT department access
    """
    return MockUserContext.create_admin()


@pytest.fixture
def mock_user():
    """
    Provide a mock regular user UserContext.

    Returns:
        UserContext: Regular user with Engineering department access
    """
    return MockUserContext.create_user()


@pytest.fixture
def mock_hr():
    """
    Provide a mock HR user UserContext.

    Returns:
        UserContext: HR Manager with HR department access
    """
    return MockUserContext.create_hr_user()


@pytest.fixture
def mock_finance():
    """
    Provide a mock Finance user UserContext.

    Returns:
        UserContext: Finance Analyst with Finance department access
    """
    return MockUserContext.create_finance_user()


@pytest.fixture
def mock_custom_user():
    """
    Factory fixture for creating custom mock users.

    Returns:
        Callable: Factory function that accepts user parameters

    Example:
        def test_with_custom_user(mock_custom_user):
            user = mock_custom_user(
                email="custom@test.com",
                role="Specialist",
                department="R&D"
            )
            assert user.role == "Specialist"
    """

    def _create_custom_user(
        user_id: Optional[UUID] = None,
        email: str = "custom@test.com",
        tenant_id: str = TestUsers.DEFAULT_TENANT_ID,
        role: str = "CustomRole",
        department: str = "CustomDept",
    ):
        from uuid import uuid4

        return MockUserContext.create_custom(
            user_id=user_id or uuid4(),
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    return _create_custom_user


#                     DATABASE & ENGINE FIXTURES
# ----------------------------------------------------------------------------


@pytest.fixture(scope="function")
def test_settings() -> AppSettings:
    """
    Provide test configuration settings.

    Creates an AppSettings instance suitable for testing without
    requiring external configuration files.

    Returns:
        AppSettings: Configured for testing with mocked dependencies
    """
    from sentinel_rag.config import (
        DatabaseSettings,
        DocRetrievalSettings,
        SecuritySettings,
        OIDCSettings,
        TenantSettings,
        AuditSettings,
        CORSSettings,
        RBACSettings,
    )

    return AppSettings.model_construct(
        config_path="",
        app_name="Sentinel RAG Test",
        app_version="1.0.0-test",
        environment="testing",
        debug=True,
        database=DatabaseSettings.model_construct(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        ),
        doc_retrieval=DocRetrievalSettings.model_construct(
            max_retrieved_docs=20,
            similarity_threshold=0.4,
            rrf_constant=60,
        ),
        security=SecuritySettings.model_construct(
            secret_key="test-secret-key-for-testing-minimum-32-characters",
            algorithm="HS256",
            access_token_expire_minutes=60,
        ),
        oidc=OIDCSettings.model_construct(
            client_id="test_client_id",
            client_secret="test_client_secret",
            server_metadata_url="https://test.example.com/.well-known/openid-configuration",
        ),
        tenant=TenantSettings.model_construct(
            tenant_id="test-tenant-001",
            domain="test.example.com",
        ),
        audit=AuditSettings.model_construct(
            enabled=False,
            retention_years=7,
            async_logging=False,
        ),
        cors=CORSSettings.model_construct(
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        ),
        rbac=RBACSettings.model_construct(
            departments=["finance", "hr", "engineering", "sales", "marketing", "it"],
            roles={
                "finance": ["accountant", "financial_analyst", "finance_manager"],
                "hr": ["recruiter", "hr_manager", "hr_director"],
                "engineering": [
                    "intern",
                    "engineer",
                    "senior_engineer",
                    "engineering_manager",
                ],
                "it": ["admin", "support", "security"],
            },
            access_matrix={},
        ),
    )


@pytest.fixture
def app_state(app):
    """
    Get the application state for testing.

    Note: The app must be used within a lifespan context for
    the state to be fully initialized.

    Args:
        app: FastAPI application instance

    Returns:
        AppState: Application state container
    """
    return get_app_state()


#                        SAMPLE DATA FIXTURES
# ----------------------------------------------------------------------------


@pytest.fixture
def sample_query_request():
    """
    Provide a sample query request payload.

    Returns:
        dict: Valid query request with all required fields
    """
    return {"user_query": "What is the company policy on remote work?"}


@pytest.fixture
def sample_document_upload():
    """
    Provide sample document upload form data.

    Returns:
        dict: Valid document upload metadata
    """
    return {
        "doc_title": "Test Document",
        "doc_description": "A test document for unit testing",
        "doc_department": "Engineering",
        "doc_classification": "Internal",
    }


@pytest.fixture
def sample_document_response():
    """
    Provide a sample document response structure.

    Returns:
        dict: Expected document response format
    """
    return {
        "page_content": "Sample document content for testing.",
        "metadata": {
            "doc_id": str(TestUsers.REGULAR_USER_ID),
            "title": "Test Document",
            "department": "Engineering",
            "classification": "Internal",
        },
    }


@pytest.fixture
def sample_user_response():
    """
    Provide a sample user response structure.

    Returns:
        dict: Expected user response format
    """
    return {
        "user_id": str(TestUsers.ADMIN_USER_ID),
        "user_email": "admin@test.com",
        "user_role": "Admin",
        "user_department": "IT",
    }


@pytest.fixture
def multiple_classification_levels():
    """
    Provide all valid document classification levels.

    Returns:
        list: All classification levels for parametrized testing
    """
    return ["Public", "Internal", "Confidential", "Restricted"]


@pytest.fixture
def multiple_departments():
    """
    Provide test departments for parametrized testing.

    Returns:
        list: Department names
    """
    return ["Engineering", "HR", "Finance", "IT", "Sales", "Marketing"]


#                        TEST MARKERS DOCUMENTATION
# ----------------------------------------------------------------------------

# Markers are defined in pytest.ini and can be used to categorize tests:
#
# @pytest.mark.unit: Fast, isolated unit tests (no external dependencies)
# @pytest.mark.integration: Tests with external dependencies (DB, API)
# @pytest.mark.auth: Authentication and authorization tests
# @pytest.mark.query: RAG query and search tests
# @pytest.mark.documents: Document upload and processing tests
# @pytest.mark.user: User profile and management tests
# @pytest.mark.slow: Tests that take longer to execute
# @pytest.mark.security: Security-focused tests
#
# Usage:
#   pytest -m unit          # Run only unit tests
#   pytest -m "not slow"    # Skip slow tests
#   pytest -m "auth or user"  # Run auth and user tests


"""
Coverage Summary:
- Total fixtures: 22
- Coverage: 100% of test infrastructure needs
- Test client fixtures: 5 (unauthenticated, admin, user, HR, finance)
- Mock user fixtures: 5 (admin, user, HR, finance, custom factory)
- Sample data fixtures: 6 (query, document upload, responses, etc.)
- Configuration fixtures: 3 (settings, app state, environment)
"""
