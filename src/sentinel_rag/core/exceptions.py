"""
Custom exceptions for the Sentinel RAG system.

This module provides domain-specific exceptions for better error handling
and debugging across the application.

"""

try:
    from ..exceptions import SentinelError
except (ImportError, ValueError):
    # Fallback
    class CoreError(Exception):
        pass


# Seeder Errors
class SeederError(SentinelError or CoreError):
    """Base exception for seeder-related errors."""

    pass


# RBAC Configuration Errors
class RbacConfigError(SentinelError or CoreError):
    """Exception raised when RBAC configuration is invalid or missing."""

    pass


# Engine Initialization Errors
class EngineError(SentinelError or CoreError):
    """Exception raised during SentinelEngine initialization."""

    pass


# Document Processing Errors
class DocumentError(SentinelError or CoreError):
    """Base exception for document processing errors."""

    pass


class DocumentProcessorError(DocumentError):
    """Exception raised when document processing fails."""

    pass


class DocumentIngestionError(DocumentError):
    """Exception raised when document ingestion fails."""

    pass


# Query Errors
class QueryError(SentinelError or CoreError):
    """Base exception for query-related errors."""

    pass
