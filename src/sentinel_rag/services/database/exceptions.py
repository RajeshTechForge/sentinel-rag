"""
Exceptions Class for the Database Manager.
"""

try:
    from ...exceptions import SentinelError
except (ImportError, ValueError):
    # Fallback
    class DatabaseManagerError(Exception):
        pass


class DatabaseError(SentinelError or DatabaseManagerError):
    pass
