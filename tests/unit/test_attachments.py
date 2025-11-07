import sys
import os
from unittest.mock import Mock
import pytest
from datetime import datetime, timezone

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import attachments_bp
from backend.api import attachments as attachments_module


# app, client, and mock_db fixtures provided by conftest.py


class TestNowIso:
    """Test the now_iso helper function."""
    
    def test_now_iso_returns_iso_format(self):
        """Test that now_iso returns a valid ISO format string."""
        result = attachments_module.now_iso()
        
        # Verify it's a string
        assert isinstance(result, str)
        
        # Verify it can be parsed as ISO format
        parsed = datetime.fromisoformat(result.replace('Z', '+00:00'))
        assert isinstance(parsed, datetime)
    
    def test_now_iso_includes_timezone(self):
        """Test that now_iso includes timezone information."""
        result = attachments_module.now_iso()
        
        # ISO format with timezone should contain '+' or 'Z'
        assert '+' in result or 'Z' in result.upper()


class TestAddAttachment:
    """Test the add_attachment endpoint."""
    
    def test_add_attachment_success(self, client, mock_db, monkeypatch):
        """Test successfully adding an attachment."""
        # Mock Firestore
        mock_doc_ref = Mock()
        mock_doc_ref.id = "attachment123"
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test data
        payload = {
            "task_id": "task1",
            "filename": "document.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "uploaded_by": "user1",
            "file_data": "base64encodeddata",
            "file_hash": "hash123"
        }
        
        response = client.post(
            "/api/attachments",
            json=payload,
            content_type="application/json"
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.get_json()
        assert data["attachment_id"] == "attachment123"
        assert data["task_id"] == "task1"
        assert data["filename"] == "document.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["uploaded_by"] == "user1"
        assert "uploaded_at" in data
        
        # Verify Firestore was called correctly
        mock_db.collection.assert_called_once_with("attachments")
        mock_collection.document.assert_called_once()
        mock_doc_ref.set.assert_called_once()
    
    def test_add_attachment_missing_task_id(self, client, mock_db, monkeypatch):
        """Test adding attachment without task_id."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "file_name": "document.pdf",
            "file_path": "gs://bucket/document.pdf",
            "uploaded_by": "user1"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "task_id" in data["error"]
    
    def test_add_attachment_missing_file_name(self, client, mock_db, monkeypatch):
        """Test adding attachment without filename."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "uploaded_by": "user1",
            "file_data": "base64encodeddata"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "filename" in data["error"]
    
    def test_add_attachment_missing_file_path(self, client, mock_db, monkeypatch):
        """Test adding attachment without file_data."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "filename": "document.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "uploaded_by": "user1"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "file_data" in data["error"]
    
    def test_add_attachment_missing_uploaded_by(self, client, mock_db, monkeypatch):
        """Test adding attachment without uploaded_by."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "file_name": "document.pdf",
            "file_path": "gs://bucket/document.pdf"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "uploaded_by" in data["error"]
    
    def test_add_attachment_empty_strings(self, client, mock_db, monkeypatch):
        """Test adding attachment with empty string values."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "  ",
            "file_name": "",
            "file_path": "gs://bucket/document.pdf",
            "uploaded_by": "user1"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_add_attachment_no_payload(self, client, mock_db, monkeypatch):
        """Test adding attachment with no JSON payload."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post("/api/attachments")
        
        assert response.status_code == 400
        data = response.get_json()
        # The endpoint uses force=True and returns {} if no JSON, so all fields will be missing
        if data:
            assert "error" in data
    
    def test_add_attachment_whitespace_trimmed(self, client, mock_db, monkeypatch):
        """Test that whitespace is trimmed from input fields."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "attachment456"
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "  task1  ",
            "filename": "  document.pdf  ",
            "mime_type": "  application/pdf  ",
            "size_bytes": 1024,
            "uploaded_by": "  user1  ",
            "file_data": "base64encodeddata"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        
        # Verify trimmed values
        assert data["task_id"] == "task1"
        assert data["filename"] == "document.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["uploaded_by"] == "user1"


class TestListAttachments:
    """Test the list_attachments endpoint."""
    
    def test_list_attachments_success(self, client, mock_db, monkeypatch):
        """Test successfully listing attachments for a task."""
        # Mock Firestore documents
        mock_doc1 = Mock()
        mock_doc1.id = "attachment1"
        mock_doc1.to_dict = Mock(return_value={
            "task_id": "task1",
            "filename": "doc1.pdf",
            "mime_type": "application/pdf",
            "uploaded_by": "user1",
            "uploaded_at": "2025-01-01T00:00:00+00:00"
        })
        
        mock_doc2 = Mock()
        mock_doc2.id = "attachment2"
        mock_doc2.to_dict = Mock(return_value={
            "task_id": "task1",
            "filename": "doc2.pdf",
            "mime_type": "application/pdf",
            "uploaded_by": "user2",
            "uploaded_at": "2025-01-02T00:00:00+00:00"
        })
        
        # Mock query chain
        mock_query = Mock()
        mock_query.stream = Mock(return_value=[mock_doc1, mock_doc2])
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_query)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/attachments/by-task/task1")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify response
        assert len(data) == 2
        assert data[0]["attachment_id"] == "attachment1"
        assert data[0]["filename"] == "doc1.pdf"
        assert data[1]["attachment_id"] == "attachment2"
        assert data[1]["filename"] == "doc2.pdf"
        
        # Verify Firestore query (FieldFilter syntax uses filter parameter)
        mock_db.collection.assert_called_once_with("attachments")
        assert mock_collection.where.called
        mock_where.order_by.assert_called_once_with("uploaded_at", direction='DESCENDING')
    
    def test_list_attachments_empty_result(self, client, mock_db, monkeypatch):
        """Test listing attachments when no attachments exist."""
        # Mock empty query result
        mock_query = Mock()
        mock_query.stream = Mock(return_value=[])
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_query)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/attachments/by-task/task999")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []
    
    def test_list_attachments_single_result(self, client, mock_db, monkeypatch):
        """Test listing attachments with a single result."""
        mock_doc = Mock()
        mock_doc.id = "attachment_only"
        mock_doc.to_dict = Mock(return_value={
            "task_id": "task1",
            "file_name": "single.pdf",
            "file_path": "gs://bucket/single.pdf",
            "uploaded_by": "user1",
            "upload_date": "2025-01-01T00:00:00+00:00"
        })
        
        mock_query = Mock()
        mock_query.stream = Mock(return_value=[mock_doc])
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_query)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/attachments/by-task/task1")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["attachment_id"] == "attachment_only"
        assert data[0]["file_name"] == "single.pdf"
    
    def test_list_attachments_ordered_by_date(self, client, mock_db, monkeypatch):
        """Test that attachments are ordered by uploaded_at."""
        mock_query = Mock()
        mock_query.stream = Mock(return_value=[])
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_query)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        client.get("/api/attachments/by-task/task1")
        
        # Verify order_by was called with uploaded_at
        mock_where.order_by.assert_called_once_with("uploaded_at", direction='DESCENDING')
    
    def test_list_attachments_index_error_fallback(self, client, mock_db, monkeypatch):
        """Test fallback when Firestore index is missing."""
        # Mock documents to return
        mock_doc1 = Mock()
        mock_doc1.id = "attachment1"
        mock_doc1.to_dict = Mock(return_value={
            "task_id": "task1",
            "file_name": "doc1.pdf",
            "file_path": "gs://bucket/doc1.pdf",
            "uploaded_by": "user1",
            "upload_date": "2025-01-01T00:00:00+00:00"
        })
        
        # Mock query that raises index error, then fallback query that works
        mock_fallback_query = Mock()
        mock_fallback_query.stream = Mock(return_value=[mock_doc1])
        
        mock_ordered_query = Mock()
        mock_ordered_query.stream = Mock(side_effect=Exception("requires an index for task_id"))
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_ordered_query)
        mock_where.stream = Mock(return_value=[mock_doc1])  # Fallback without ordering
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/attachments/by-task/task1")
        
        # Should succeed with fallback
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["attachment_id"] == "attachment1"
        
        # Verify fallback was used (stream called on where object, not ordered query)
        mock_where.stream.assert_called_once()
    
    def test_list_attachments_non_index_error_raised(self, client, mock_db, monkeypatch):
        """Test that non-index errors are raised (not caught by fallback)."""
        # Mock query that raises a non-index error
        mock_ordered_query = Mock()
        mock_ordered_query.stream = Mock(side_effect=Exception("database connection failed"))
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_ordered_query)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # The exception should bubble up and Flask will catch it
        with pytest.raises(Exception, match="database connection failed"):
            attachments_module.list_attachments("task1")
    
    def test_list_attachments_index_error_fallback_sorting(self, client, mock_db, monkeypatch):
        """Test that fallback sorting works correctly when index is missing."""
        # Mock documents with different upload dates
        mock_doc1 = Mock()
        mock_doc1.id = "attachment1"
        mock_doc1.to_dict = Mock(return_value={
            "task_id": "task1",
            "filename": "older.pdf",
            "uploaded_by": "user1",
            "uploaded_at": "2025-01-01T00:00:00+00:00"
        })
        
        mock_doc2 = Mock()
        mock_doc2.id = "attachment2"
        mock_doc2.to_dict = Mock(return_value={
            "task_id": "task1",
            "filename": "newer.pdf",
            "uploaded_by": "user1",
            "uploaded_at": "2025-01-02T00:00:00+00:00"
        })
        
        # Mock query that raises index error, then fallback query that works
        mock_ordered_query = Mock()
        mock_ordered_query.stream = Mock(side_effect=Exception("requires an index for task_id"))
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_ordered_query)
        # Return documents in wrong order to test sorting
        mock_where.stream = Mock(return_value=[mock_doc1, mock_doc2])  # older first
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/attachments/by-task/task1")
        
        # Should succeed with fallback and proper sorting
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        # Should be sorted by uploaded_at descending (newer first)
        assert data[0]["filename"] == "newer.pdf"
        assert data[1]["filename"] == "older.pdf"
    
    def test_list_attachments_index_error_fallback_no_dates(self, client, mock_db, monkeypatch):
        """Test fallback sorting when some documents lack uploaded_at."""
        mock_doc1 = Mock()
        mock_doc1.id = "attachment1"
        mock_doc1.to_dict = Mock(return_value={
            "task_id": "task1",
            "filename": "no_date.pdf",
            "uploaded_by": "user1"
            # No uploaded_at field
        })
        
        mock_doc2 = Mock()
        mock_doc2.id = "attachment2"
        mock_doc2.to_dict = Mock(return_value={
            "task_id": "task1",
            "filename": "with_date.pdf",
            "uploaded_by": "user1",
            "uploaded_at": "2025-01-01T00:00:00+00:00"
        })
        
        mock_ordered_query = Mock()
        mock_ordered_query.stream = Mock(side_effect=Exception("requires an index"))
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_ordered_query)
        mock_where.stream = Mock(return_value=[mock_doc1, mock_doc2])
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/attachments/by-task/task1")
        
        # Should succeed with fallback
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        # Documents with dates should sort first (descending order), then documents without dates
        assert data[0]["filename"] == "with_date.pdf"
        assert data[1]["filename"] == "no_date.pdf"


class TestBlueprintRegistration:
    """Test that the blueprint is properly configured."""
    
    def test_blueprint_url_prefix(self):
        """Test that the blueprint has the correct URL prefix."""
        assert attachments_bp.url_prefix == "/api/attachments"
    
    def test_blueprint_name(self):
        """Test that the blueprint has the correct name."""
        assert attachments_bp.name == "attachments"


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_add_attachment_with_special_characters_in_filename(self, client, mock_db, monkeypatch):
        """Test adding attachment with special characters in filename."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "attachment789"
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "filename": "résumé-2025_v1.2.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "uploaded_by": "user1",
            "file_data": "base64encodeddata"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["filename"] == "résumé-2025_v1.2.pdf"
    
    def test_add_attachment_with_long_file_path(self, client, mock_db, monkeypatch):
        """Test adding attachment with very long filename."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "attachment999"
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        long_filename = "a" * 200 + ".pdf"
        payload = {
            "task_id": "task1",
            "filename": long_filename,
            "mime_type": "application/pdf",
            "size_bytes": 1024,
            "uploaded_by": "user1",
            "file_data": "base64encodeddata"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["filename"] == long_filename


class TestIsAllowedFile:
    """Test the is_allowed_file validation function."""
    
    def test_is_allowed_file_valid_pdf(self):
        """Test valid PDF file."""
        result, message = attachments_module.is_allowed_file("document.pdf", "application/pdf", 1024)
        assert result is True
        assert message == "OK"
    
    def test_is_allowed_file_valid_image(self):
        """Test valid image file."""
        result, message = attachments_module.is_allowed_file("photo.jpg", "image/jpeg", 2048)
        assert result is True
        assert message == "OK"
    
    def test_is_allowed_file_missing_filename(self):
        """Test with missing filename."""
        result, message = attachments_module.is_allowed_file("", "application/pdf", 1024)
        assert result is False
        assert message == "Missing filename or MIME type"
    
    def test_is_allowed_file_missing_mime_type(self):
        """Test with missing MIME type."""
        result, message = attachments_module.is_allowed_file("document.pdf", "", 1024)
        assert result is False
        assert message == "Missing filename or MIME type"
    
    def test_is_allowed_file_file_too_large(self):
        """Test file size exceeding MAX_FILE_SIZE."""
        large_size = attachments_module.MAX_FILE_SIZE + 1
        result, message = attachments_module.is_allowed_file("large.pdf", "application/pdf", large_size)
        assert result is False
        assert "File size exceeds" in message
    
    def test_is_allowed_file_blocked_extension(self):
        """Test blocked file extension."""
        result, message = attachments_module.is_allowed_file("script.exe", "application/octet-stream", 1024)
        assert result is False
        assert "File type not allowed" in message
        assert ".exe" in message
    
    def test_is_allowed_file_disallowed_extension(self):
        """Test disallowed file extension."""
        result, message = attachments_module.is_allowed_file("document.xyz", "application/octet-stream", 1024)
        assert result is False
        assert "File type not supported" in message
        assert ".xyz" in message
    
    def test_is_allowed_file_invalid_mime_type(self):
        """Test invalid MIME type."""
        result, message = attachments_module.is_allowed_file("document.pdf", "application/javascript", 1024)
        assert result is False
        assert "MIME type not allowed" in message
    
    def test_is_allowed_file_case_insensitive_extension(self):
        """Test that extension checking is case insensitive."""
        result, message = attachments_module.is_allowed_file("document.PDF", "application/pdf", 1024)
        assert result is True
        assert message == "OK"
    
    def test_is_allowed_file_blocked_case_insensitive(self):
        """Test that blocked extension checking is case insensitive."""
        result, message = attachments_module.is_allowed_file("script.EXE", "application/octet-stream", 1024)
        assert result is False
        assert "File type not allowed" in message
    
    def test_add_attachment_file_too_large_encoded(self, client, mock_db, monkeypatch):
        """Test adding attachment with file_data too large for Firestore."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Create a large base64 string (>900KB)
        large_data = "a" * 950000  # ~950KB
        
        payload = {
            "task_id": "task1",
            "filename": "large.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,  # Original size is small, but encoded is large
            "uploaded_by": "user1",
            "file_data": large_data
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "File too large for Firestore storage" in data["error"]
    
    def test_add_attachment_invalid_file_validation(self, client, mock_db, monkeypatch):
        """Test adding attachment with invalid file (blocked extension)."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "filename": "script.exe",
            "mime_type": "application/octet-stream",
            "size_bytes": 1024,
            "uploaded_by": "user1",
            "file_data": "base64encodeddata"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "File type not allowed" in data["error"]
    
    def test_add_attachment_invalid_mime_type(self, client, mock_db, monkeypatch):
        """Test adding attachment with invalid MIME type."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "filename": "document.pdf",
            "mime_type": "application/javascript",
            "size_bytes": 1024,
            "uploaded_by": "user1",
            "file_data": "base64encodeddata"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "MIME type not allowed" in data["error"]
