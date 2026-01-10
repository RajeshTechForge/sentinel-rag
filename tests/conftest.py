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
from sentinel_rag.api.dependencies import get_app_state
from sentinel_rag.services.auth import get_current_active_user
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
def admin_client(app) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as an Admin user.
    
    This client bypasses OIDC authentication and uses a mock admin user.
    
    Args:
        app: FastAPI application instance
        
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
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def user_client(app) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as a regular User.
    
    This client uses a mock user from the Engineering department.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        TestClient authenticated as regular user
    """
    mock_user = MockUserContext.create_user()
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        mock_user
    )
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def hr_client(app) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as an HR department user.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        TestClient authenticated as HR user
    """
    mock_hr = MockUserContext.create_hr_user()
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        mock_hr
    )
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def finance_client(app) -> Generator[TestClient, None, None]:
    """
    Create a TestClient authenticated as a Finance department user.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        TestClient authenticated as Finance user
    """
    mock_finance = MockUserContext.create_finance_user()
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        mock_finance
    )
    
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
    app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(
        user_context
    )
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
