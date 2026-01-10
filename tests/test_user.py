"""
Tests for user profile endpoints.

Tests the /api/user endpoints to ensure they return correct user
information and work properly with mock authentication.
"""

import pytest


@pytest.mark.user
@pytest.mark.integration
class TestUserEndpoints:
    """Test suite for user profile endpoints."""

    def test_get_current_user_admin(self, admin_client):
        """Test that admin user can retrieve their profile."""
        response = admin_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "test-admin-001"
        assert data["user_email"] == "admin@test.com"
        assert data["user_role"] == "Admin"
        assert data["user_department"] == "IT"

    def test_get_current_user_regular_user(self, user_client):
        """Test that regular user can retrieve their profile."""
        response = user_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "test-user-001"
        assert data["user_email"] == "user@test.com"
        assert data["user_role"] == "User"
        assert data["user_department"] == "Engineering"

    def test_get_current_user_hr(self, hr_client):
        """Test that HR user can retrieve their profile."""
        response = hr_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        assert data["user_role"] == "Manager"
        assert data["user_department"] == "HR"

    def test_get_current_user_finance(self, finance_client):
        """Test that Finance user can retrieve their profile."""
        response = finance_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        assert data["user_role"] == "Analyst"
        assert data["user_department"] == "Finance"

    def test_get_current_user_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.post("/api/user")

        assert response.status_code == 401

    def test_user_response_schema(self, admin_client):
        """Test that user response follows the expected schema."""
        response = admin_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields are present
        required_fields = ["user_id", "user_email", "user_role", "user_department"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify field types
        assert isinstance(data["user_id"], str)
        assert isinstance(data["user_email"], str)
        assert isinstance(data["user_role"], str)
        assert isinstance(data["user_department"], str)

        # Verify email format (basic check)
        assert "@" in data["user_email"]

    # def test_get_user_documents_endpoint_exists(self, admin_client):
    #     """Test that the user documents endpoint is accessible."""
    #     # This endpoint should exist and be protected by auth
    #     response = admin_client.post("/api/user/docs")

    #     # Should not be 404 or 401 (endpoint exists and we're authenticated)
    #     # May be 200 with empty list, or other status depending on database state
    #     assert response.status_code != 404
    #     assert response.status_code != 401

    def test_different_users_have_different_profiles(self, app):
        """Test that different mock users return different profile data."""
        from tests.conftest import create_custom_client
        from tests.test_utils import MockUserContext

        # Create two different users
        user1 = MockUserContext.create_custom(
            user_id="unique-user-1",
            email="unique1@test.com",
            tenant_id="tenant-1",
            role="Engineer",
            department="Engineering",
        )

        user2 = MockUserContext.create_custom(
            user_id="unique-user-2",
            email="unique2@test.com",
            tenant_id="tenant-1",
            role="Manager",
            department="Management",
        )

        # Get profile for user1
        client1 = create_custom_client(app, user1)
        response1 = client1.post("/api/user")
        data1 = response1.json()

        # Clear overrides and get profile for user2
        app.dependency_overrides.clear()
        client2 = create_custom_client(app, user2)
        response2 = client2.post("/api/user")
        data2 = response2.json()

        # Verify they're different
        assert data1["user_id"] != data2["user_id"]
        assert data1["user_email"] != data2["user_email"]
        assert data1["user_role"] != data2["user_role"]
        assert data1["user_department"] != data2["user_department"]

    def test_mock_user_context_matches_response(self, app, mock_admin):
        """Test that the mock context values match the API response."""
        from tests.conftest import create_custom_client

        client = create_custom_client(app, mock_admin)
        response = client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        # Response should match the mock user context
        assert data["user_id"] == mock_admin.user_id
        assert data["user_email"] == mock_admin.email
        assert data["user_role"] == mock_admin.role
        assert data["user_department"] == mock_admin.department
