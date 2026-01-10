"""
Tests for authentication bypass and mock user contexts.

This module validates that our testing infrastructure correctly
bypasses OIDC authentication using dependency_overrides.
"""

import pytest
from tests.test_utils import MockUserContext


@pytest.mark.auth
@pytest.mark.unit
class TestMockAuthentication:
    """Test suite for mock authentication functionality."""

    def test_admin_user_context_creation(self, mock_admin):
        """Test that mock admin user context is created correctly."""
        assert mock_admin.user_id == "test-admin-001"
        assert mock_admin.email == "admin@test.com"
        assert mock_admin.role == "Admin"
        assert mock_admin.department == "IT"
        assert mock_admin.tenant_id == "test-tenant-001"

    def test_regular_user_context_creation(self, mock_user):
        """Test that mock regular user context is created correctly."""
        assert mock_user.user_id == "test-user-001"
        assert mock_user.email == "user@test.com"
        assert mock_user.role == "User"
        assert mock_user.department == "Engineering"

    def test_hr_user_context_creation(self, mock_hr):
        """Test that mock HR user context is created correctly."""
        assert mock_hr.role == "Manager"
        assert mock_hr.department == "HR"

    def test_finance_user_context_creation(self, mock_finance):
        """Test that mock Finance user context is created correctly."""
        assert mock_finance.role == "Analyst"
        assert mock_finance.department == "Finance"

    def test_custom_user_context_creation(self):
        """Test creating a custom user context with specific parameters."""
        custom_user = MockUserContext.create_custom(
            user_id="custom-123",
            email="custom@example.com",
            tenant_id="tenant-999",
            role="CustomRole",
            department="CustomDept",
        )

        assert custom_user.user_id == "custom-123"
        assert custom_user.email == "custom@example.com"
        assert custom_user.tenant_id == "tenant-999"
        assert custom_user.role == "CustomRole"
        assert custom_user.department == "CustomDept"

    def test_user_context_pydantic_validation(self):
        """Test that UserContext enforces Pydantic validation."""
        # This should succeed - all required fields provided
        valid_user = MockUserContext.create_custom(
            user_id="test-001",
            email="test@example.com",
            tenant_id="tenant-001",
            role="TestRole",
            department="TestDept",
        )
        assert valid_user is not None

        # Test that Pydantic validates properly
        # UserContext should reject invalid data if validation is strict
        from sentinel_rag.services.auth import UserContext

        # Valid creation
        user = UserContext(
            user_id="valid-id",
            email="valid@test.com",
            tenant_id="tenant-1",
            role="Role",
            department="Dept",
        )
        assert user.user_id == "valid-id"


@pytest.mark.auth
@pytest.mark.integration
class TestAuthenticationBypass:
    """Test that dependency_overrides correctly bypasses authentication."""

    def test_admin_client_bypass(self, admin_client):
        """Test that admin_client successfully bypasses authentication."""
        # The /api/user endpoint requires authentication
        response = admin_client.post("/api/user")

        # Should succeed without providing actual OIDC token
        assert response.status_code == 200
        data = response.json()

        # Verify we get the mock admin user data
        assert data["user_id"] == "test-admin-001"
        assert data["user_email"] == "admin@test.com"
        assert data["user_role"] == "Admin"
        assert data["user_department"] == "IT"

    def test_user_client_bypass(self, user_client):
        """Test that user_client successfully bypasses authentication."""
        response = user_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "test-user-001"
        assert data["user_email"] == "user@test.com"
        assert data["user_role"] == "User"
        assert data["user_department"] == "Engineering"

    def test_hr_client_bypass(self, hr_client):
        """Test that hr_client successfully bypasses authentication."""
        response = hr_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        assert data["user_role"] == "Manager"
        assert data["user_department"] == "HR"

    def test_finance_client_bypass(self, finance_client):
        """Test that finance_client successfully bypasses authentication."""
        response = finance_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        assert data["user_role"] == "Analyst"
        assert data["user_department"] == "Finance"

    def test_unauthenticated_client_fails(self, client):
        """Test that requests without authentication are rejected."""
        # Using the base client without auth override
        response = client.post("/api/user")

        # Should be unauthorized
        assert response.status_code == 401
        assert "not authenticated" in response.json()["message"].lower()

    def test_different_users_in_same_session(self, app):
        """Test that we can switch between different users in tests."""
        from tests.conftest import create_custom_client

        # Create client with first user
        user1 = MockUserContext.create_custom(
            user_id="user-1",
            email="user1@test.com",
            tenant_id="tenant-1",
            role="Role1",
            department="Dept1",
        )
        client1 = create_custom_client(app, user1)

        response1 = client1.post("/api/user")
        assert response1.status_code == 200
        assert response1.json()["user_id"] == "user-1"

        # Clear and create client with second user
        app.dependency_overrides.clear()

        user2 = MockUserContext.create_custom(
            user_id="user-2",
            email="user2@test.com",
            tenant_id="tenant-1",
            role="Role2",
            department="Dept2",
        )
        client2 = create_custom_client(app, user2)

        response2 = client2.post("/api/user")
        assert response2.status_code == 200
        assert response2.json()["user_id"] == "user-2"
