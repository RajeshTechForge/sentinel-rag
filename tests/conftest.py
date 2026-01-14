"""
Pytest configuration and fixtures for Sentinel RAG testing.

This module provides:
- Test client fixtures with and without authentication
- Mock user contexts for different roles
- Database and engine fixtures
- Dependency override utilities
"""

import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient

from sentinel_rag.api.app import create_application
from sentinel_rag.api.dependencies import (
    get_app_state,
    get_current_active_user,
    get_settings_dep,
)
from sentinel_rag.config import AppSettings
from tests.test_utils import MockUserContext, create_mock_get_current_user


# ========================================
#           ENVIRONMENT SETUP
# ========================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up test environment variables.

    This runs once per test session before any tests execute.
    """
    # Ensure we're using test configuration
    os.environ.setdefault("TESTING", "true")

    # Disable audit logging in tests to avoid database overhead
    # Unless explicitly testing audit functionality
    os.environ.setdefault("AUDIT_ENABLED", "false")

    yield

    # Cleanup after all tests
    pass


# ========================================
#         APPLICATION FIXTURES
# ========================================


@pytest.fixture(scope="function")
def app():
    """
    Create a fresh FastAPI application instance for each test.

    This ensures test isolation by creating a new app instance
    for each test function.

    Returns:
        FastAPI application instance
    """
    application = create_application()

    yield application

    # Clear dependency overrides after each test
    application.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(app) -> Generator[TestClient, None, None]:
    """
    Create a TestClient without authentication.

    Use this for testing public endpoints or when you want to
    manually handle authentication in the test.

    Args:
        app: FastAPI application instance

    Returns:
        TestClient instance

    Example:
        ```python
        def test_health_check(client):
            response = client.get("/health")
            assert response.status_code == 200
        ```
    """
    with TestClient(app) as test_client:
        yield test_client


# ========================================
#      AUTHENTICATED CLIENT FIXTURES
# ========================================


@pytest.fixture(scope="function")
def admin_client(app, test_settings) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as an Admin user.

    This client bypasses OIDC authentication and uses a mock admin user.

    Args:
        app: FastAPI application instance
        test_settings: Test configuration settings

    Returns:
        TestClient authenticated as admin

    Example:
        ```python
        def test_admin_access(admin_client):
            response = admin_client.post("/api/user")
            assert response.status_code == 200
            assert response.json()["user_role"] == "Admin"
        ```
    """
    mock_admin = MockUserContext.create_admin()
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        mock_admin
    )
    app.dependency_overrides[get_settings_dep] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def user_client(app, test_settings) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as a regular User.

    This client uses a mock user from the Engineering department.

    Args:
        app: FastAPI application instance
        test_settings: Test configuration settings

    Returns:
        TestClient authenticated as regular user
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
    Create a TestClient authenticated as an HR department user.

    Args:
        app: FastAPI application instance
        test_settings: Test configuration settings

    Returns:
        TestClient authenticated as HR user
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
    Create a TestClient authenticated as a Finance department user.

    Args:
        app: FastAPI application instance
        test_settings: Test configuration settings

    Returns:
        TestClient authenticated as Finance user
    """
    mock_finance = MockUserContext.create_finance_user()
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        mock_finance
    )
    app.dependency_overrides[get_settings_dep] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_custom_client(app, user_context):
    """
    Helper to create a client with a custom user context.

    This is useful when you need a specific user configuration
    that isn't covered by the predefined fixtures.

    Args:
        app: FastAPI application instance
        user_context: UserContext to use for authentication

    Returns:
        TestClient authenticated with the provided user context

    Example:
        ```python
        def test_custom_user(app):
            custom_user = MockUserContext.create_custom(
                user_id="custom-001",
                email="custom@test.com",
                tenant_id="tenant-002",
                role="CustomRole",
                department="CustomDept"
            )
            client = create_custom_client(app, custom_user)
            response = client.post("/api/user")
            assert response.json()["user_role"] == "CustomRole"
        ```
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

    # Create minimal test settings using model_construct to bypass Pydantic validation
    test_settings = AppSettings.model_construct(
        config_path="",
        app_name="Test",
        app_version="1.0.0",
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
        tenant=TenantSettings.model_construct(tenant_id="test", domain="test.com"),
        audit=AuditSettings.model_construct(enabled=False),
        cors=CORSSettings.model_construct(),
        rbac=RBACSettings.model_construct(departments=[], roles={}, access_matrix={}),
    )

    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        user_context
    )
    app.dependency_overrides[get_settings_dep] = lambda: test_settings
    return TestClient(app)


# ========================================
#         MOCK USER FIXTURES
# ========================================


@pytest.fixture
def mock_admin():
    """Provide a mock admin UserContext."""
    return MockUserContext.create_admin()


@pytest.fixture
def mock_user():
    """Provide a mock regular user UserContext."""
    return MockUserContext.create_user()


@pytest.fixture
def mock_hr():
    """Provide a mock HR user UserContext."""
    return MockUserContext.create_hr_user()


@pytest.fixture
def mock_finance():
    """Provide a mock Finance user UserContext."""
    return MockUserContext.create_finance_user()


# ========================================
#      DATABASE & ENGINE FIXTURES
# ========================================


@pytest.fixture(scope="function")
def test_settings() -> AppSettings:
    """
    Provide test configuration settings.

    This creates an AppSettings instance suitable for testing,
    without requiring a config.json file to exist.

    Returns:
        AppSettings configured for testing
    """
    from sentinel_rag.config import (
        DatabaseSettings,
        SecuritySettings,
        OIDCSettings,
        TenantSettings,
        AuditSettings,
        CORSSettings,
        RBACSettings,
    )

    # Use model_construct to bypass validation for nested settings
    return AppSettings.model_construct(
        config_path="",  # Empty path for tests
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
            enabled=False,  # Disable audit in tests
            retention_years=7,
            async_logging=False,
        ),
        cors=CORSSettings.model_construct(),
        rbac=RBACSettings.model_construct(
            departments=["finance", "hr", "engineering", "sales", "marketing"],
            roles={
                "finance": ["accountant", "financial_analyst", "finance_manager"],
                "hr": ["recruiter", "hr_manager", "hr_director"],
                "engineering": [
                    "intern",
                    "engineer",
                    "senior_engineer",
                    "engineering_manager",
                ],
            },
            access_matrix={},
        ),
    )


@pytest.fixture
def app_state(app):
    """
    Get the application state for testing.

    This provides access to the database, engine, and audit service.
    Note: The app must be used within a lifespan context for this to work.

    Args:
        app: FastAPI application instance

    Returns:
        AppState instance
    """
    return get_app_state()


# ========================================
#         HELPER FIXTURES
# ========================================


@pytest.fixture
def sample_query_request():
    """Provide a sample query request payload."""
    return {
        "user_query": "What is the company policy on remote work?",
        "k": 5,
    }


@pytest.fixture
def sample_document_upload():
    """Provide sample document upload data."""
    return {
        "doc_title": "Test Document",
        "doc_description": "A test document for unit testing",
        "doc_department": "Engineering",
        "doc_classification": "Internal",
    }


# ========================================
#            TEST MARKERS
# ========================================

# Markers are defined in pytest.ini and can be used to categorize tests:
# - @pytest.mark.unit: Fast, isolated unit tests
# - @pytest.mark.integration: Integration tests with database
# - @pytest.mark.auth: Authentication-related tests
# - @pytest.mark.query: Query/RAG engine tests
# - @pytest.mark.documents: Document upload tests
# - @pytest.mark.user: User profile tests
