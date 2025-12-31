"""
Exceptions Class for the Database Manager.
"""

try:
    from ...exceptions import SentinelError
except (ImportError, ValueError):
    # Fallback
    class DatabaseManagerError(Exception):
        pass


# Database Errors
class DatabaseError(SentinelError or DatabaseManagerError):
    """Base exception for database-related errors."""

    pass
