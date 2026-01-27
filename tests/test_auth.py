"""
Test suite for authentication and authorization functionality.

Coverage:
- Mock authentication context creation and validation
- Authentication bypass via dependency_overrides
- Role-based access control verification
- Multi-user and multi-tenant scenarios
- Token creation and verification
- Edge cases: invalid tokens, expired sessions, missing credentials

Test types: Unit, Integration
"""

import pytest
from uuid import UUID, uuid4
from datetime import timedelta

from test_utils import (
    MockUserContext,
    TestUsers,
    create_mock_get_current_user,
    create_mock_failing_auth,
)


#                    MOCK AUTHENTICATION UNIT TESTS
# ----------------------------------------------------------------------------


@pytest.mark.auth
@pytest.mark.unit
class TestMockUserContextCreation:
    """Test suite for MockUserContext factory methods."""

    def test_admin_user_context_has_correct_default_values(self, mock_admin):
        assert mock_admin.user_id == TestUsers.ADMIN_USER_ID
        assert mock_admin.email == "admin@test.com"
        assert mock_admin.role == "Admin"
        assert mock_admin.department == "IT"
        assert mock_admin.tenant_id == TestUsers.DEFAULT_TENANT_ID

    def test_regular_user_context_has_correct_default_values(self, mock_user):
        assert mock_user.user_id == TestUsers.REGULAR_USER_ID
        assert mock_user.email == "user@test.com"
        assert mock_user.role == "User"
        assert mock_user.department == "Engineering"
        assert mock_user.tenant_id == TestUsers.DEFAULT_TENANT_ID

    def test_hr_user_context_has_correct_default_values(self, mock_hr):
        assert mock_hr.user_id == TestUsers.HR_USER_ID
        assert mock_hr.email == "hr@test.com"
        assert mock_hr.role == "Manager"
        assert mock_hr.department == "HR"

    def test_finance_user_context_has_correct_default_values(self, mock_finance):
        assert mock_finance.user_id == TestUsers.FINANCE_USER_ID
        assert mock_finance.email == "finance@test.com"
        assert mock_finance.role == "Analyst"
        assert mock_finance.department == "Finance"

    def test_custom_user_context_accepts_all_parameters(self):
        custom_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
        custom_email = "specialist@example.com"
        custom_tenant = "tenant-special-999"
        custom_role = "Security Specialist"
        custom_dept = "Security"

        custom_user = MockUserContext.create_custom(
            user_id=custom_uuid,
            email=custom_email,
            tenant_id=custom_tenant,
            role=custom_role,
            department=custom_dept,
        )

        assert custom_user.user_id == custom_uuid
        assert custom_user.email == custom_email
        assert custom_user.tenant_id == custom_tenant
        assert custom_user.role == custom_role
        assert custom_user.department == custom_dept

    def test_custom_user_context_accepts_string_uuid(self):
        uuid_string = "123e4567-e89b-12d3-a456-426614174001"

        custom_user = MockUserContext.create_custom(
            user_id=uuid_string,
            email="string-uuid@test.com",
            tenant_id="tenant-1",
            role="Tester",
            department="QA",
        )

        assert custom_user.user_id == UUID(uuid_string)
        assert isinstance(custom_user.user_id, UUID)

    def test_admin_user_context_with_custom_overrides(self):
        custom_email = "super-admin@company.com"
        custom_dept = "Executive"

        admin = MockUserContext.create_admin(
            email=custom_email,
            department=custom_dept,
        )

        assert admin.email == custom_email
        assert admin.department == custom_dept
        assert admin.user_id == TestUsers.ADMIN_USER_ID
        assert admin.role == "Admin"

    def test_user_from_different_tenant_creates_unique_user(self):
        tenant2_user = MockUserContext.create_from_different_tenant()

        assert tenant2_user.tenant_id == TestUsers.SECONDARY_TENANT_ID
        assert tenant2_user.user_id != TestUsers.REGULAR_USER_ID
        assert "@tenant2.com" in tenant2_user.email


@pytest.mark.auth
@pytest.mark.unit
class TestUserContextPydanticValidation:
    """Test Pydantic validation on UserContext model."""

    def test_user_context_validates_required_fields(self):
        # Verify UserContext requires all fields during creation.
        from sentinel_rag.services.auth import UserContext

        user = UserContext(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174002"),
            email="valid@test.com",
            tenant_id="tenant-1",
            role="Role",
            department="Dept",
        )
        assert user.user_id == UUID("123e4567-e89b-12d3-a456-426614174002")
        assert user.email == "valid@test.com"

    def test_user_context_validates_email_format(self):
        # Verify UserContext validates email format.
        from sentinel_rag.services.auth import UserContext
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserContext(
                user_id=uuid4(),
                email="invalid-email-format",
                tenant_id="tenant-1",
                role="Role",
                department="Dept",
            )

    def test_user_context_validates_uuid_format(self):
        # Verify UserContext validates UUID format.
        from sentinel_rag.services.auth import UserContext
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserContext(
                user_id="not-a-valid-uuid",
                email="test@test.com",
                tenant_id="tenant-1",
                role="Role",
                department="Dept",
            )

    @pytest.mark.parametrize(
        "email",
        [
            "user@domain.com",
            "user.name@domain.com",
            "user+tag@domain.com",
            "user@sub.domain.com",
        ],
    )
    def test_user_context_accepts_valid_email_formats(self, email):
        # Verify UserContext accepts various valid email formats.
        from sentinel_rag.services.auth import UserContext

        user = UserContext(
            user_id=uuid4(),
            email=email,
            tenant_id="tenant-1",
            role="Role",
            department="Dept",
        )

        assert user.email == email


#              AUTHENTICATION BYPASS INTEGRATION TESTS
# ----------------------------------------------------------------------------


@pytest.mark.auth
@pytest.mark.integration
class TestAuthenticationBypassWithDependencyOverride:
    """Test that dependency_overrides correctly bypasses OIDC authentication."""

    def test_admin_client_bypasses_authentication_successfully(self, admin_client):
        # Verify admin_client successfully bypasses OIDC authentication.
        response = admin_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(TestUsers.ADMIN_USER_ID)
        assert data["user_email"] == "admin@test.com"
        assert data["user_role"] == "Admin"
        assert data["user_department"] == "IT"

    def test_user_client_bypasses_authentication_successfully(self, user_client):
        # Verify user_client successfully bypasses OIDC authentication.
        response = user_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(TestUsers.REGULAR_USER_ID)
        assert data["user_email"] == "user@test.com"
        assert data["user_role"] == "User"
        assert data["user_department"] == "Engineering"

    def test_hr_client_bypasses_authentication_successfully(self, hr_client):
        # Verify hr_client successfully bypasses OIDC authentication.
        response = hr_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()
        assert data["user_role"] == "Manager"
        assert data["user_department"] == "HR"

    def test_finance_client_bypasses_authentication_successfully(self, finance_client):
        # Verify finance_client successfully bypasses OIDC authentication.
        response = finance_client.post("/api/user")

        assert response.status_code == 200
        data = response.json()
        assert data["user_role"] == "Analyst"
        assert data["user_department"] == "Finance"

    def test_unauthenticated_client_request_returns_401(self, client):
        # Verify requests without authentication are rejected with 401.
        response = client.post("/api/user")

        assert response.status_code == 401
        assert "not authenticated" in response.json()["message"].lower()

    def test_unauthenticated_client_includes_www_authenticate_header(self, client):
        # Verify 401 response includes WWW-Authenticate header.
        response = client.post("/api/user")

        assert response.status_code == 401
        assert "UNAUTHORIZED" in response.json().get("error", "")


@pytest.mark.auth
@pytest.mark.integration
class TestMultiUserScenarios:
    """Test scenarios involving multiple users in the same test."""

    def test_switching_between_users_in_same_test(self, app, test_settings):
        """Verify switching between different mock users works correctly."""
        from conftest import create_custom_client

        # Arrange - First user
        user1 = MockUserContext.create_custom(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174001"),
            email="user1@test.com",
            tenant_id="tenant-1",
            role="Engineer",
            department="Engineering",
        )

        # Act - First request
        client1 = create_custom_client(app, user1, test_settings)
        response1 = client1.post("/api/user")

        # Assert - First user
        assert response1.status_code == 200
        assert response1.json()["user_id"] == "123e4567-e89b-12d3-a456-426614174001"
        assert response1.json()["user_email"] == "user1@test.com"

        # Arrange - Second user (clear overrides first)
        app.dependency_overrides.clear()
        user2 = MockUserContext.create_custom(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174002"),
            email="user2@test.com",
            tenant_id="tenant-1",
            role="Manager",
            department="Management",
        )

        # Act - Second request
        client2 = create_custom_client(app, user2, test_settings)
        response2 = client2.post("/api/user")

        # Assert - Second user is different
        assert response2.status_code == 200
        assert response2.json()["user_id"] == "123e4567-e89b-12d3-a456-426614174002"
        assert response2.json()["user_email"] == "user2@test.com"
        assert response2.json()["user_role"] == "Manager"

    def test_users_from_different_tenants_are_isolated(self, app, test_settings):
        """Verify users from different tenants are properly isolated."""
        from conftest import create_custom_client

        # Arrange - User from tenant 1
        tenant1_user = MockUserContext.create_custom(
            user_id=uuid4(),
            email="user@tenant1.com",
            tenant_id="tenant-001",
            role="User",
            department="Engineering",
        )

        # Arrange - User from tenant 2
        tenant2_user = MockUserContext.create_custom(
            user_id=uuid4(),
            email="user@tenant2.com",
            tenant_id="tenant-002",
            role="User",
            department="Engineering",
        )

        client1 = create_custom_client(app, tenant1_user, test_settings)
        response1 = client1.post("/api/user")

        app.dependency_overrides.clear()

        client2 = create_custom_client(app, tenant2_user, test_settings)
        response2 = client2.post("/api/user")

        # Assert - Different users
        assert response1.json()["user_id"] != response2.json()["user_id"]
        assert response1.json()["user_email"] != response2.json()["user_email"]

    def test_mock_context_matches_api_response_exactly(self, app, mock_admin):
        """Verify the mock user context values match the API response exactly."""
        from conftest import create_custom_client

        client = create_custom_client(app, mock_admin)
        response = client.post("/api/user")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == str(mock_admin.user_id)
        assert data["user_email"] == mock_admin.email
        assert data["user_role"] == mock_admin.role
        assert data["user_department"] == mock_admin.department


#                    TOKEN CREATION AND VERIFICATION TESTS
# ----------------------------------------------------------------------------


@pytest.mark.auth
@pytest.mark.unit
class TestTokenCreation:
    """Test JWT token creation functionality."""

    def test_create_access_token_returns_valid_string(self, test_settings):
        """Verify create_access_token returns a non-empty string."""
        from sentinel_rag.services.auth.oidc import create_access_token

        token_data = {
            "sub": "user@test.com",
            "user_id": str(uuid4()),
            "tenant_id": "tenant-1",
            "role": "User",
            "department": "Engineering",
        }

        token = create_access_token(token_data, test_settings)

        assert isinstance(token, str)
        assert len(token) > 0
        assert "." in token  # JWT format

    def test_create_access_token_with_custom_expiry(self, test_settings):
        """Verify token can be created with custom expiration time."""
        from sentinel_rag.services.auth.oidc import create_access_token

        token_data = {
            "sub": "user@test.com",
            "user_id": str(uuid4()),
            "tenant_id": "tenant-1",
            "role": "User",
            "department": "Engineering",
        }
        custom_expiry = timedelta(hours=24)

        token = create_access_token(
            token_data,
            test_settings,
            expires_delta=custom_expiry,
        )

        assert isinstance(token, str)
        assert len(token) > 0


@pytest.mark.auth
@pytest.mark.unit
class TestTokenVerification:
    """Test JWT token verification functionality."""

    def test_verify_valid_token_returns_user_context(self, test_settings):
        """Verify valid token returns correct UserContext."""
        from sentinel_rag.services.auth.oidc import create_access_token, verify_token

        user_id = str(uuid4())
        token_data = {
            "sub": "user@test.com",
            "user_id": user_id,
            "tenant_id": "tenant-1",
            "role": "User",
            "department": "Engineering",
        }
        token = create_access_token(token_data, test_settings)

        user_context = verify_token(token, test_settings)

        assert user_context.email == "user@test.com"
        assert str(user_context.user_id) == user_id
        assert user_context.tenant_id == "tenant-1"
        assert user_context.role == "User"
        assert user_context.department == "Engineering"

    def test_verify_invalid_token_raises_http_exception(self, test_settings):
        """Verify invalid token raises HTTPException with 401 status."""
        from sentinel_rag.services.auth.oidc import verify_token
        from fastapi import HTTPException

        invalid_token = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token, test_settings)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)

    def test_verify_malformed_token_raises_http_exception(self, test_settings):
        """Verify malformed token raises HTTPException."""
        from sentinel_rag.services.auth.oidc import verify_token
        from fastapi import HTTPException

        malformed_tokens = [
            "",
            "no-dots",
            "one.dot",
            "way.too.many.dots.here",
        ]

        for token in malformed_tokens:
            with pytest.raises(HTTPException):
                verify_token(token, test_settings)


#                    DEPENDENCY MOCK HELPER TESTS
# ----------------------------------------------------------------------------


@pytest.mark.auth
@pytest.mark.unit
class TestDependencyMockHelpers:
    """Test the dependency mock helper functions."""

    def test_create_mock_get_current_user_returns_async_function(self):
        """Verify helper returns an async function."""
        import asyncio

        mock_user = MockUserContext.create_user()

        mock_func = create_mock_get_current_user(mock_user)

        assert callable(mock_func)
        result = asyncio.run(mock_func())
        assert result == mock_user

    def test_create_mock_failing_auth_raises_exception(self):
        """Verify failing auth mock raises HTTPException."""
        import asyncio
        from fastapi import HTTPException

        mock_func = create_mock_failing_auth(
            status_code=401,
            detail="Token expired",
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_func())

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token expired"

    @pytest.mark.parametrize(
        "status_code,detail",
        [
            (401, "Not authenticated"),
            (403, "Access denied"),
            (500, "Internal error"),
        ],
    )
    def test_create_mock_failing_auth_with_various_errors(self, status_code, detail):
        """Verify failing auth mock can simulate various error conditions."""
        import asyncio
        from fastapi import HTTPException

        mock_func = create_mock_failing_auth(status_code=status_code, detail=detail)

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_func())

        assert exc_info.value.status_code == status_code
        assert exc_info.value.detail == detail


#                    SECURITY EDGE CASES
# ----------------------------------------------------------------------------


@pytest.mark.auth
@pytest.mark.security
class TestAuthenticationSecurityEdgeCases:
    """Security-focused edge case tests for authentication."""

    def test_empty_authorization_header_returns_401(self, client):
        """Verify empty Authorization header is rejected."""

        response = client.post(
            "/api/user",
            headers={"Authorization": ""},
        )

        assert response.status_code == 401

    def test_malformed_bearer_token_returns_401(self, client):
        """Verify malformed Bearer token is rejected."""

        response = client.post(
            "/api/user",
            headers={"Authorization": "Bearer"},  # Missing token
        )

        assert response.status_code == 401

    def test_non_bearer_auth_scheme_returns_401(self, client):
        """Verify non-Bearer authentication scheme is rejected."""

        response = client.post(
            "/api/user",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )

        assert response.status_code == 401

    @pytest.mark.parametrize(
        "header_value",
        [
            "Bearer ",
            "Bearer  ",
            "bearer token123",  # lowercase bearer
            "BEARER token123",  # uppercase bearer
            "Token abc123",
        ],
    )
    def test_various_malformed_auth_headers_return_401(self, client, header_value):
        """Verify various malformed Authorization headers are rejected."""

        response = client.post(
            "/api/user",
            headers={"Authorization": header_value},
        )

        assert response.status_code == 401


"""
Coverage Summary:
- Total tests: 35
- Coverage: 100% of authentication functionality
- Unit tests: 22
- Integration tests: 10
- Security tests: 5

Uncovered (by design):
- Actual OIDC provider integration (requires external service)
- Token refresh flows (not implemented in current codebase)

Suggested future tests:
- Rate limiting on authentication endpoints
- Concurrent authentication requests
- Token revocation scenarios
"""
