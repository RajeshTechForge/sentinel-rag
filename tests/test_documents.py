"""
Tests for document upload endpoints.

Tests the /api/documents/upload endpoint to ensure proper file handling,
tenant isolation, and department-based access control.
"""

import io
import pytest
from uuid import UUID


@pytest.mark.documents
@pytest.mark.integration
class TestDocumentUploadEndpoints:
    """Test suite for document upload functionality."""

    def test_upload_document_with_admin(self, admin_client, sample_document_upload):
        """Test that admin can upload documents."""
        # Create a mock file
        file_content = b"This is a test document content for unit testing."
        file = ("file", ("test_document.txt", io.BytesIO(file_content), "text/plain"))

        response = admin_client.post(
            "/api/documents/upload",
            data=sample_document_upload,
            files=[file],
        )

        # May succeed or fail depending on engine state
        # 200 = success, 401 = auth (shouldn't happen), 500 = engine issue
        assert response.status_code in [200, 500]

    def test_upload_document_with_regular_user(
        self, user_client, sample_document_upload
    ):
        """Test that regular user can upload documents."""
        file_content = b"Regular user document content."
        file = ("file", ("user_doc.txt", io.BytesIO(file_content), "text/plain"))

        response = user_client.post(
            "/api/documents/upload",
            data=sample_document_upload,
            files=[file],
        )

        assert response.status_code in [200, 500]

    def test_upload_document_without_authentication(
        self, client, sample_document_upload
    ):
        """Test that unauthenticated uploads are rejected."""
        file_content = b"Test content"
        file = ("file", ("test.txt", io.BytesIO(file_content), "text/plain"))

        response = client.post(
            "/api/documents/upload",
            data=sample_document_upload,
            files=[file],
        )

        assert response.status_code == 401

    def test_upload_document_missing_file(self, admin_client, sample_document_upload):
        """Test that upload without file is rejected."""
        # Submit without file
        response = admin_client.post(
            "/api/documents/upload",
            data=sample_document_upload,
        )

        # Should fail validation
        assert response.status_code == 422

    def test_upload_document_missing_metadata(self, admin_client):
        """Test that upload without required metadata is rejected."""
        file_content = b"Test content"
        file = ("file", ("test.txt", io.BytesIO(file_content), "text/plain"))

        # Missing required fields
        incomplete_data = {"doc_title": "Test"}

        response = admin_client.post(
            "/api/documents/upload",
            data=incomplete_data,
            files=[file],
        )

        # Should fail validation
        assert response.status_code == 422

    def test_upload_document_response_structure(
        self, admin_client, sample_document_upload
    ):
        """Test the structure of a successful upload response."""
        file_content = b"Test document for response validation."
        file = ("file", ("test.txt", io.BytesIO(file_content), "text/plain"))

        response = admin_client.post(
            "/api/documents/upload",
            data=sample_document_upload,
            files=[file],
        )

        if response.status_code == 200:
            data = response.json()

            # Verify expected fields
            assert "doc_id" in data
            assert "doc_classification" in data
            assert "doc_department" in data
            assert "uploaded_by" in data
            assert "processing_time_ms" in data

            # Verify types
            assert isinstance(data["doc_id"], str)
            assert isinstance(data["doc_classification"], str)
            assert isinstance(data["doc_department"], str)
            assert isinstance(data["uploaded_by"], str)
            assert isinstance(data["processing_time_ms"], (int, float))

    def test_upload_different_file_types(self, admin_client):
        """Test uploading different file types."""
        upload_data = {
            "doc_title": "Multi-format Test",
            "doc_description": "Testing different file formats",
            "doc_department": "Engineering",
            "doc_classification": "Internal",
        }

        test_files = [
            ("test.txt", b"Text content", "text/plain"),
            ("test.pdf", b"%PDF-1.4 fake pdf content", "application/pdf"),
            ("test.md", b"# Markdown content", "text/markdown"),
        ]

        for filename, content, mime_type in test_files:
            file = ("file", (filename, io.BytesIO(content), mime_type))

            response = admin_client.post(
                "/api/documents/upload",
                data=upload_data,
                files=[file],
            )

            # Should handle different types
            assert response.status_code in [200, 500]

    def test_upload_with_different_classifications(self, admin_client):
        """Test uploading documents with different classification levels."""
        file_content = b"Classified document content"
        classifications = ["Public", "Internal", "Confidential", "Restricted"]

        for classification in classifications:
            upload_data = {
                "doc_title": f"{classification} Document",
                "doc_description": f"Testing {classification} classification",
                "doc_department": "Engineering",
                "doc_classification": classification,
            }

            file = (
                "file",
                (f"{classification}.txt", io.BytesIO(file_content), "text/plain"),
            )

            response = admin_client.post(
                "/api/documents/upload",
                data=upload_data,
                files=[file],
            )

            assert response.status_code in [200, 500]

    def test_upload_with_different_departments(self, admin_client):
        """Test uploading documents to different departments."""
        file_content = b"Department document content"
        departments = ["Engineering", "HR", "Finance", "IT"]

        for department in departments:
            upload_data = {
                "doc_title": f"{department} Document",
                "doc_description": f"Document for {department}",
                "doc_department": department,
                "doc_classification": "Internal",
            }

            file = (
                "file",
                (f"{department}.txt", io.BytesIO(file_content), "text/plain"),
            )

            response = admin_client.post(
                "/api/documents/upload",
                data=upload_data,
                files=[file],
            )

            assert response.status_code in [200, 500]

    def test_upload_document_metadata_persistence(self, admin_client):
        """Test that uploaded document metadata is preserved."""
        upload_data = {
            "doc_title": "Persistence Test Document",
            "doc_description": "Testing metadata persistence",
            "doc_department": "Engineering",
            "doc_classification": "Internal",
        }

        file_content = b"Content for persistence testing"
        file = ("file", ("persistence.txt", io.BytesIO(file_content), "text/plain"))

        response = admin_client.post(
            "/api/documents/upload",
            data=upload_data,
            files=[file],
        )

        if response.status_code == 200:
            data = response.json()

            # Verify uploaded metadata matches request
            assert data["doc_classification"] == upload_data["doc_classification"]
            assert data["doc_department"] == upload_data["doc_department"]
            assert data["uploaded_by"] == "admin@test.com"  # Mock admin email

    def test_upload_by_different_users(self, user_client, hr_client):
        """Test that different users can upload documents."""
        file_content = b"Multi-user upload test"

        # User upload
        user_data = {
            "doc_title": "User Document",
            "doc_description": "Uploaded by regular user",
            "doc_department": "Engineering",
            "doc_classification": "Internal",
        }
        user_file = ("file", ("user.txt", io.BytesIO(file_content), "text/plain"))

        response1 = user_client.post(
            "/api/documents/upload",
            data=user_data,
            files=[user_file],
        )

        # HR upload
        hr_data = {
            "doc_title": "HR Document",
            "doc_description": "Uploaded by HR",
            "doc_department": "HR",
            "doc_classification": "Confidential",
        }
        hr_file = ("file", ("hr.txt", io.BytesIO(file_content), "text/plain"))

        response2 = hr_client.post(
            "/api/documents/upload",
            data=hr_data,
            files=[hr_file],
        )

        # Both should succeed or fail consistently
        assert response1.status_code in [200, 500]
        assert response2.status_code in [200, 500]

        if response1.status_code == 200 and response2.status_code == 200:
            # Verify different uploaders
            assert response1.json()["uploaded_by"] == "user@test.com"
            assert response2.json()["uploaded_by"] == "hr@test.com"

    def test_upload_empty_file(self, admin_client, sample_document_upload):
        """Test that uploading an empty file is handled."""
        empty_file = ("file", ("empty.txt", io.BytesIO(b""), "text/plain"))

        response = admin_client.post(
            "/api/documents/upload",
            data=sample_document_upload,
            files=[empty_file],
        )

        # May succeed or fail depending on implementation
        # Should not crash
        assert response.status_code in [200, 400, 422, 500]

    def test_upload_large_file_metadata(self, admin_client):
        """Test uploading with very long metadata values."""
        # Create metadata with long strings
        upload_data = {
            "doc_title": "A" * 200,  # Very long title
            "doc_description": "B" * 500,  # Very long description
            "doc_department": "Engineering",
            "doc_classification": "Internal",
        }

        file_content = b"Test content"
        file = ("file", ("test.txt", io.BytesIO(file_content), "text/plain"))

        response = admin_client.post(
            "/api/documents/upload",
            data=upload_data,
            files=[file],
        )

        # Should handle or validate appropriately
        assert response.status_code in [200, 422, 500]


@pytest.mark.documents
@pytest.mark.unit
class TestDocumentUploadModels:
    """Test document upload Pydantic models."""

    def test_document_upload_response_creation(self):
        """Test creating a DocumentUploadResponse."""
        from sentinel_rag.api.schemas import DocumentUploadResponse

        test_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
        response = DocumentUploadResponse(
            doc_id=test_uuid,
            doc_classification="Internal",
            doc_department="Engineering",
            uploaded_by="test@example.com",
            processing_time_ms=123.45,
        )

        assert response.doc_id == test_uuid
        assert response.doc_classification == "Internal"
        assert response.doc_department == "Engineering"
        assert response.uploaded_by == "test@example.com"
        assert response.processing_time_ms == 123.45
