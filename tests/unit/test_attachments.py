import sys
import os
import types
from unittest.mock import Mock, MagicMock, patch
import pytest
from datetime import datetime, timezone

# Ensure repo root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Mock firebase_admin before importing
fake_firebase = types.ModuleType("firebase_admin")
fake_firebase._apps = []

fake_credentials = types.ModuleType("firebase_admin.credentials")
def _dummy_certificate(path):
    class _C: pass
    return _C()

fake_credentials.Certificate = _dummy_certificate
fake_firebase.credentials = fake_credentials
fake_firebase.initialize_app = lambda cred: None

fake_firestore = types.ModuleType("firebase_admin.firestore")
fake_firestore.client = Mock()
fake_firebase.firestore = fake_firestore

sys.modules["firebase_admin"] = fake_firebase
sys.modules["firebase_admin.credentials"] = fake_credentials
sys.modules["firebase_admin.firestore"] = fake_firestore

from flask import Flask
from backend.api import attachments_bp
from backend.api import attachments as attachments_module


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(attachments_bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def mock_db():
    """Create a mock Firestore database."""
    mock_db = Mock()
    mock_collection = Mock()
    mock_db.collection = Mock(return_value=mock_collection)
    return mock_db


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
            "file_name": "document.pdf",
            "file_path": "gs://bucket/document.pdf",
            "uploaded_by": "user1"
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
        assert data["file_name"] == "document.pdf"
        assert data["file_path"] == "gs://bucket/document.pdf"
        assert data["uploaded_by"] == "user1"
        assert "upload_date" in data
        
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
        """Test adding attachment without file_name."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "file_path": "gs://bucket/document.pdf",
            "uploaded_by": "user1"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "file_name" in data["error"]
    
    def test_add_attachment_missing_file_path(self, client, mock_db, monkeypatch):
        """Test adding attachment without file_path."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "file_name": "document.pdf",
            "uploaded_by": "user1"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "file_path" in data["error"]
    
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
            "file_name": "  document.pdf  ",
            "file_path": "  gs://bucket/document.pdf  ",
            "uploaded_by": "  user1  "
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        
        # Verify trimmed values
        assert data["task_id"] == "task1"
        assert data["file_name"] == "document.pdf"
        assert data["file_path"] == "gs://bucket/document.pdf"
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
            "file_name": "doc1.pdf",
            "file_path": "gs://bucket/doc1.pdf",
            "uploaded_by": "user1",
            "upload_date": "2025-01-01T00:00:00+00:00"
        })
        
        mock_doc2 = Mock()
        mock_doc2.id = "attachment2"
        mock_doc2.to_dict = Mock(return_value={
            "task_id": "task1",
            "file_name": "doc2.pdf",
            "file_path": "gs://bucket/doc2.pdf",
            "uploaded_by": "user2",
            "upload_date": "2025-01-02T00:00:00+00:00"
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
        assert data[0]["file_name"] == "doc1.pdf"
        assert data[1]["attachment_id"] == "attachment2"
        assert data[1]["file_name"] == "doc2.pdf"
        
        # Verify Firestore query
        mock_db.collection.assert_called_once_with("attachments")
        mock_collection.where.assert_called_once_with("task_id", "==", "task1")
        mock_where.order_by.assert_called_once_with("upload_date")
    
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
        """Test that attachments are ordered by upload_date."""
        mock_query = Mock()
        mock_query.stream = Mock(return_value=[])
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_query)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        client.get("/api/attachments/by-task/task1")
        
        # Verify order_by was called with upload_date
        mock_where.order_by.assert_called_once_with("upload_date")


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
            "file_name": "résumé-2025_v1.2.pdf",
            "file_path": "gs://bucket/résumé-2025_v1.2.pdf",
            "uploaded_by": "user1"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["file_name"] == "résumé-2025_v1.2.pdf"
    
    def test_add_attachment_with_long_file_path(self, client, mock_db, monkeypatch):
        """Test adding attachment with very long file path."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "attachment999"
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        long_path = "gs://bucket/" + "a" * 500 + ".pdf"
        payload = {
            "task_id": "task1",
            "file_name": "document.pdf",
            "file_path": long_path,
            "uploaded_by": "user1"
        }
        
        response = client.post("/api/attachments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["file_path"] == long_path
