"""
Testing utilities for Sentinel RAG.

Provides mock user contexts, helper functions, and common test utilities.
"""

from sentinel_rag.services.auth import UserContext


class MockUserContext:
    """Factory for creating mock user contexts for testing."""

    @staticmethod
    def create_admin(
        user_id: str = "test-admin-001",
        email: str = "admin@test.com",
        tenant_id: str = "test-tenant-001",
        role: str = "Admin",
        department: str = "IT",
    ) -> UserContext:
        """Create a mock admin user context."""
        return UserContext(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    @staticmethod
    def create_user(
        user_id: str = "test-user-001",
        email: str = "user@test.com",
        tenant_id: str = "test-tenant-001",
        role: str = "User",
        department: str = "Engineering",
    ) -> UserContext:
        """Create a mock regular user context."""
        return UserContext(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    @staticmethod
    def create_hr_user(
        user_id: str = "test-hr-001",
        email: str = "hr@test.com",
        tenant_id: str = "test-tenant-001",
        role: str = "Manager",
        department: str = "HR",
    ) -> UserContext:
        """Create a mock HR department user context."""
        return UserContext(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    @staticmethod
    def create_finance_user(
        user_id: str = "test-finance-001",
        email: str = "finance@test.com",
        tenant_id: str = "test-tenant-001",
        role: str = "Analyst",
        department: str = "Finance",
    ) -> UserContext:
        """Create a mock Finance department user context."""
        return UserContext(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )

    @staticmethod
    def create_custom(
        user_id: str,
        email: str,
        tenant_id: str,
        role: str,
        department: str,
    ) -> UserContext:
        """Create a custom mock user context with specified parameters."""
        return UserContext(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )


def create_mock_get_current_user(user_context: UserContext):
    """
    Create a mock dependency function that returns the specified user context.

    This function is used with FastAPI's dependency_overrides to bypass
    authentication during testing.

    Args:
        user_context: The UserContext to return

    Returns:
        An async function that returns the user context

    Example:
        ```python
        from sentinel_rag.services.auth import get_current_active_user

        mock_user = MockUserContext.create_admin()
        app.dependency_overrides[get_current_active_user] = create_mock_get_current_user(mock_user)
        ```
    """

    async def mock_get_current_user() -> UserContext:
        return user_context

    return mock_get_current_user
