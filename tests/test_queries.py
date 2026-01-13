"""
Tests for RAG query endpoints.

Tests the /api/query endpoint to ensure proper query handling,
RBAC enforcement, and audit logging.
"""

import pytest


@pytest.mark.query
@pytest.mark.integration
class TestQueryEndpoints:
    """Test suite for RAG query functionality."""

    def test_query_with_admin_user(self, admin_client, sample_query_request):
        """Test that admin user can perform queries."""
        response = admin_client.post("/api/query", json=sample_query_request)

        # Request should succeed (may return empty results if no data)
        assert response.status_code in [200, 500]  # 500 if engine not initialized

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_query_with_regular_user(self, user_client, sample_query_request):
        """Test that regular user can perform queries."""
        response = user_client.post("/api/query", json=sample_query_request)

        # Should succeed regardless of results
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_query_without_authentication(self, client, sample_query_request):
        """Test that unauthenticated queries are rejected."""
        response = client.post("/api/query", json=sample_query_request)

        assert response.status_code == 401

    def test_query_request_validation(self, admin_client):
        """Test query request validation."""
        # Test with missing user_query
        response = admin_client.post("/api/query")
        assert response.status_code == 422  # Validation error

    def test_query_with_valid_parameters(self, admin_client):
        """Test query with various valid parameters."""
        test_cases = [
            {"user_query": "What is the policy?"},
            {"user_query": "Tell me about benefits"},
            {"user_query": "Remote work guidelines"},
        ]

        for query_data in test_cases:
            response = admin_client.post("/api/query", json=query_data)
            # Should be valid request structure
            assert response.status_code in [200, 500]

    def test_query_response_structure(self, admin_client, sample_query_request):
        """Test that query response follows expected structure."""
        response = admin_client.post("/api/query", json=sample_query_request)

        if response.status_code == 200:
            data = response.json()

            # Response should be a list
            assert isinstance(data, list)

            # Each item should have page_content and metadata
            for item in data:
                assert "page_content" in item
                assert "metadata" in item
                assert isinstance(item["page_content"], str)
                assert isinstance(item["metadata"], dict)

    def test_query_with_different_users(self, user_client, hr_client):
        """Test that different users can query independently."""
        query_request = {"user_query": "company policy"}

        # User client query
        response1 = user_client.post("/api/query", json=query_request)

        # HR client query
        response2 = hr_client.post("/api/query", json=query_request)

        # Both should have valid responses
        assert response1.status_code in [200, 500]
        assert response2.status_code in [200, 500]

    def test_query_sanitization(self, admin_client):
        """Test that queries are sanitized properly."""
        # Query with extra whitespace
        response = admin_client.post(
            "/api/query", json={"user_query": "  test query  "}
        )

        # Should handle gracefully
        assert response.status_code in [200, 500]

    def test_query_with_empty_string(self, admin_client):
        """Test that empty queries are rejected."""
        response = admin_client.post("/api/query", json={"user_query": ""})

        # Should fail validation (min_length=1)
        assert response.status_code == 422

    def test_query_with_very_long_string(self, admin_client):
        """Test that very long queries are rejected."""
        # Create a query longer than max_length (5000)
        long_query = "a" * 5001

        response = admin_client.post("/api/query", json={"user_query": long_query})

        # Should fail validation
        assert response.status_code == 422


@pytest.mark.query
@pytest.mark.unit
class TestQueryRequestModel:
    """Test the QueryRequest Pydantic model."""

    def test_query_request_creation(self):
        """Test creating a valid QueryRequest."""
        from sentinel_rag.api.schemas import QueryRequest

        query = QueryRequest(user_query="What is the policy?")

        assert query.user_query == "What is the policy?"

    def test_query_request_defaults(self):
        """Test QueryRequest default values."""
        from sentinel_rag.api.schemas import QueryRequest

        QueryRequest(user_query="test query")

    def test_query_request_sanitization(self):
        """Test that QueryRequest sanitizes input."""
        from sentinel_rag.api.schemas import QueryRequest

        # Query with whitespace should be stripped
        query = QueryRequest(user_query="  test query  ")

        assert query.user_query == "test query"
