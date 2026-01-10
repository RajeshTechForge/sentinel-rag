"""Testing utilities for Sentinel RAG.

Provides mock user contexts, helper functions, and common test utilities.
All UUID values are properly typed and validated.
"""

from typing import Optional
from uuid import UUID
from sentinel_rag.services.auth import UserContext


# ========================================
#        TEST DATA CONSTANTS
# ========================================


class TestUsers:
    """Centralized test user UUIDs for consistency across tests.

    Using predictable nil UUIDs for easy identification in test failures.
    Each UUID's last byte indicates the user type:
    - 001: Regular user
    - 002: HR user
    - 003: Finance user
    - 004: Admin user
    """

    REGULAR_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
    HR_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
    FINANCE_USER_ID = UUID("00000000-0000-0000-0000-000000000003")
    ADMIN_USER_ID = UUID("00000000-0000-0000-0000-000000000004")

    DEFAULT_TENANT_ID = "test-tenant-001"


# ========================================
#       MOCK USER CONTEXT FACTORY
# ========================================


class MockUserContext:
    """Factory for creating mock user contexts for testing.

    This class provides convenient methods to create UserContext instances
    with proper UUID types for testing different user roles and scenarios.
    """

    @staticmethod
    def create_admin(
        user_id: Optional[UUID] = None,
        email: str = "admin@test.com",
        tenant_id: str = TestUsers.DEFAULT_TENANT_ID,
        role: str = "Admin",
        department: str = "IT",
    ) -> UserContext:
        """Create a mock admin user context.

        Args:
            user_id: UUID for the user (defaults to TestUsers.ADMIN_USER_ID)
            email: User email address
            tenant_id: Tenant identifier
            role: User role
            department: User department

        Returns:
            UserContext instance with admin privileges
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
        email: str = "user@test.com",
        tenant_id: str = TestUsers.DEFAULT_TENANT_ID,
        role: str = "User",
        department: str = "Engineering",
    ) -> UserContext:
        """Create a mock regular user context.

        Args:
            user_id: UUID for the user (defaults to TestUsers.REGULAR_USER_ID)
            email: User email address
            tenant_id: Tenant identifier
            role: User role
            department: User department

        Returns:
            UserContext instance with regular user privileges
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
        email: str = "hr@test.com",
        tenant_id: str = TestUsers.DEFAULT_TENANT_ID,
        role: str = "Manager",
        department: str = "HR",
    ) -> UserContext:
        """Create a mock HR department user context.

        Args:
            user_id: UUID for the user (defaults to TestUsers.HR_USER_ID)
            email: User email address
            tenant_id: Tenant identifier
            role: User role
            department: User department

        Returns:
            UserContext instance with HR manager privileges
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
        email: str = "finance@test.com",
        tenant_id: str = TestUsers.DEFAULT_TENANT_ID,
        role: str = "Analyst",
        department: str = "Finance",
    ) -> UserContext:
        """Create a mock Finance department user context.

        Args:
            user_id: UUID for the user (defaults to TestUsers.FINANCE_USER_ID)
            email: User email address
            tenant_id: Tenant identifier
            role: User role
            department: User department

        Returns:
            UserContext instance with finance analyst privileges
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
        user_id: UUID,
        email: str,
        tenant_id: str,
        role: str,
        department: str,
    ) -> UserContext:
        """Create a custom mock user context with specified parameters.

        Args:
            user_id: UUID for the user (required for custom users)
            email: User email address
            tenant_id: Tenant identifier
            role: User role
            department: User department

        Returns:
            UserContext instance with custom configuration

        Example:
            >>> from uuid import uuid4
            >>> custom_user = MockUserContext.create_custom(
            ...     user_id=uuid4(),
            ...     email="custom@example.com",
            ...     tenant_id="tenant-123",
            ...     role="Engineer",
            ...     department="R&D"
            ... )
        """
        return UserContext(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            role=role,
            department=department,
        )


# ========================================
#         DEPENDENCY MOCK HELPERS
# ========================================


def create_mock_get_current_user(user_context: UserContext):
    """Create a mock dependency function that returns the specified user context.

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
        app.dependency_overrides[get_current_active_user] = (
            create_mock_get_current_user(mock_user)
        )
        ```
    """

    async def mock_get_current_user() -> UserContext:
        return user_context

    return mock_get_current_user
