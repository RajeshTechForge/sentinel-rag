"""Custom exceptions for vector store operations."""


class VectorStoreError(Exception):
    """Base exception for vector store operations."""

    pass


class CollectionError(VectorStoreError):
    """Raised when collection operations fail."""

    pass


class UpsertError(VectorStoreError):
    """Raised when upsert operations fail."""

    pass


class SearchError(VectorStoreError):
    """Raised when search operations fail."""

    pass
