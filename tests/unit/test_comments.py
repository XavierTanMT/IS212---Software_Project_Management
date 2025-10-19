import sys
import os
from unittest.mock import Mock
import pytest
from datetime import datetime, timezone

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import comments_bp
from backend.api import comments as comments_module


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask('test_comments_app')
    app.config['TESTING'] = True
    # Use try-except to handle blueprint already registered
    try:
        app.register_blueprint(comments_bp)
    except AssertionError:
        # Blueprint already registered, that's okay
        pass
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


# Remove the mock_db fixture since it's now in conftest.py


class TestNowIso:
    """Test the now_iso helper function."""
    
    def test_now_iso_returns_iso_format(self):
        """Test that now_iso returns a valid ISO format string."""
        result = comments_module.now_iso()
        
        # Verify it's a string
        assert isinstance(result, str)
        
        # Verify it can be parsed as ISO format
        parsed = datetime.fromisoformat(result.replace('Z', '+00:00'))
        assert isinstance(parsed, datetime)
    
    def test_now_iso_includes_timezone(self):
        """Test that now_iso includes timezone information."""
        result = comments_module.now_iso()
        
        # ISO format with timezone should contain '+' or 'Z'
        assert '+' in result or 'Z' in result.upper()
    
    def test_now_iso_uses_utc(self):
        """Test that now_iso uses UTC timezone."""
        result = comments_module.now_iso()
        
        # Parse and verify timezone
        parsed = datetime.fromisoformat(result.replace('Z', '+00:00'))
        # Should be UTC (offset 0)
        assert parsed.utcoffset().total_seconds() == 0


class TestAddComment:
    """Test the add_comment endpoint."""
    
    def test_add_comment_success(self, client, mock_db, monkeypatch):
        """Test successfully adding a comment."""
        # Mock Firestore
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment123"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test data
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": "This is a test comment"
        }
        
        response = client.post(
            "/api/comments",
            json=payload,
            content_type="application/json"
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.get_json()
        assert data["comment_id"] == "comment123"
        assert data["task_id"] == "task1"
        assert data["author_id"] == "user1"
        assert data["body"] == "This is a test comment"
        assert "created_at" in data
        assert data["edited_at"] is None
        
        # Verify Firestore was called correctly
        mock_db.collection.assert_called_once_with("comments")
        mock_collection.document.assert_called_once()
        mock_doc_ref.set.assert_called_once()
        
        # Verify the document structure
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["task_id"] == "task1"
        assert call_args["author_id"] == "user1"
        assert call_args["body"] == "This is a test comment"
        assert "created_at" in call_args
        assert call_args["edited_at"] is None
    
    def test_add_comment_missing_task_id(self, client, mock_db, monkeypatch):
        """Test adding comment without task_id."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "author_id": "user1",
            "body": "This is a test comment"
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "task_id" in data["error"]
    
    def test_add_comment_missing_author_id(self, client, mock_db, monkeypatch):
        """Test adding comment without author_id."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "body": "This is a test comment"
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "author_id" in data["error"]
    
    def test_add_comment_missing_body(self, client, mock_db, monkeypatch):
        """Test adding comment without body."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "author_id": "user1"
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "body" in data["error"]
    
    def test_add_comment_empty_strings(self, client, mock_db, monkeypatch):
        """Test adding comment with empty string values."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "  ",
            "author_id": "",
            "body": "This is a test comment"
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_add_comment_whitespace_only_body(self, client, mock_db, monkeypatch):
        """Test adding comment with whitespace-only body."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": "   "
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_add_comment_no_payload(self, client, mock_db, monkeypatch):
        """Test adding comment with no JSON payload."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post("/api/comments")
        
        assert response.status_code == 400
        data = response.get_json()
        # The endpoint uses force=True and returns {} if no JSON, so all fields will be missing
        if data:
            assert "error" in data
    
    def test_add_comment_whitespace_trimmed(self, client, mock_db, monkeypatch):
        """Test that whitespace is trimmed from input fields."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment456"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "  task1  ",
            "author_id": "  user1  ",
            "body": "  This is a test comment  "
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        
        # Verify trimmed values
        assert data["task_id"] == "task1"
        assert data["author_id"] == "user1"
        assert data["body"] == "This is a test comment"
    
    def test_add_comment_sets_edited_at_to_none(self, client, mock_db, monkeypatch):
        """Test that edited_at is initially set to None."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment789"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": "New comment"
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["edited_at"] is None


class TestListComments:
    """Test the list_comments endpoint."""
    
    def test_list_comments_success(self, client, mock_db, monkeypatch):
        """Test successfully listing comments for a task."""
        # Mock Firestore documents
        mock_doc1 = Mock()
        mock_doc1.id = "comment1"
        mock_doc1.to_dict = Mock(return_value={
            "task_id": "task1",
            "author_id": "user1",
            "body": "First comment",
            "created_at": "2025-01-01T00:00:00+00:00",
            "edited_at": None
        })
        
        mock_doc2 = Mock()
        mock_doc2.id = "comment2"
        mock_doc2.to_dict = Mock(return_value={
            "task_id": "task1",
            "author_id": "user2",
            "body": "Second comment",
            "created_at": "2025-01-02T00:00:00+00:00",
            "edited_at": None
        })
        
        # Mock query chain - .stream() returns an iterable directly
        mock_limit = Mock()
        mock_limit.stream = Mock(return_value=[mock_doc1, mock_doc2])
        
        mock_order_by = Mock()
        mock_order_by.limit = Mock(return_value=mock_limit)
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_order_by)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/comments/by-task/task1")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify response
        assert len(data) == 2
        assert data[0]["comment_id"] == "comment1"
        assert data[0]["body"] == "First comment"
        assert data[1]["comment_id"] == "comment2"
        assert data[1]["body"] == "Second comment"
        
        # Verify Firestore query
        mock_db.collection.assert_called_once_with("comments")
        mock_collection.where.assert_called_once_with("task_id", "==", "task1")
        mock_where.order_by.assert_called_once_with("created_at")
        mock_order_by.limit.assert_called_once_with(100)
    
    def test_list_comments_empty_result(self, client, mock_db, monkeypatch):
        """Test listing comments when no comments exist."""
        # Mock empty query result - .stream() returns empty list
        mock_limit = Mock()
        mock_limit.stream = Mock(return_value=[])
        
        mock_order_by = Mock()
        mock_order_by.limit = Mock(return_value=mock_limit)
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_order_by)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/comments/by-task/task999")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []
    
    def test_list_comments_single_result(self, client, mock_db, monkeypatch):
        """Test listing comments with a single result."""
        mock_doc = Mock()
        mock_doc.id = "comment_only"
        mock_doc.to_dict = Mock(return_value={
            "task_id": "task1",
            "author_id": "user1",
            "body": "Only comment",
            "created_at": "2025-01-01T00:00:00+00:00",
            "edited_at": None
        })
        
        mock_limit = Mock()
        mock_limit.stream = Mock(return_value=[mock_doc])
        
        mock_order_by = Mock()
        mock_order_by.limit = Mock(return_value=mock_limit)
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_order_by)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/comments/by-task/task1")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["comment_id"] == "comment_only"
        assert data[0]["body"] == "Only comment"
    
    def test_list_comments_ordered_by_created_at(self, client, mock_db, monkeypatch):
        """Test that comments are ordered by created_at."""
        mock_limit = Mock()
        mock_limit.stream = Mock(return_value=[])
        
        mock_order_by = Mock()
        mock_order_by.limit = Mock(return_value=mock_limit)
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_order_by)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        client.get("/api/comments/by-task/task1")
        
        # Verify order_by was called with created_at
        mock_where.order_by.assert_called_once_with("created_at")
    
    def test_list_comments_limited_to_100(self, client, mock_db, monkeypatch):
        """Test that comments are limited to 100 results."""
        mock_limit = Mock()
        mock_limit.stream = Mock(return_value=[])
        
        mock_order_by = Mock()
        mock_order_by.limit = Mock(return_value=mock_limit)
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_order_by)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        client.get("/api/comments/by-task/task1")
        
        # Verify limit was called with 100
        mock_order_by.limit.assert_called_once_with(100)
    
    def test_list_comments_with_edited_comments(self, client, mock_db, monkeypatch):
        """Test listing comments that have been edited."""
        mock_doc = Mock()
        mock_doc.id = "comment_edited"
        mock_doc.to_dict = Mock(return_value={
            "task_id": "task1",
            "author_id": "user1",
            "body": "Edited comment",
            "created_at": "2025-01-01T00:00:00+00:00",
            "edited_at": "2025-01-02T00:00:00+00:00"
        })
        
        mock_limit = Mock()
        mock_limit.stream = Mock(return_value=[mock_doc])
        
        mock_order_by = Mock()
        mock_order_by.limit = Mock(return_value=mock_limit)
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_order_by)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/comments/by-task/task1")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["edited_at"] == "2025-01-02T00:00:00+00:00"


class TestBlueprintRegistration:
    """Test that the blueprint is properly configured."""
    
    def test_blueprint_url_prefix(self):
        """Test that the blueprint has the correct URL prefix."""
        assert comments_bp.url_prefix == "/api/comments"
    
    def test_blueprint_name(self):
        """Test that the blueprint has the correct name."""
        assert comments_bp.name == "comments"


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_add_comment_with_long_body(self, client, mock_db, monkeypatch):
        """Test adding comment with very long body text."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment_long"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        long_body = "A" * 5000  # 5000 character comment
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": long_body
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["body"] == long_body
    
    def test_add_comment_with_special_characters(self, client, mock_db, monkeypatch):
        """Test adding comment with special characters."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment_special"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        special_body = "Comment with émojis 😀🎉 and symbols: @#$%^&*()"
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": special_body
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["body"] == special_body
    
    def test_add_comment_with_newlines(self, client, mock_db, monkeypatch):
        """Test adding comment with newline characters."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment_newlines"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        multiline_body = "Line 1\nLine 2\nLine 3"
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": multiline_body
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["body"] == multiline_body
    
    def test_list_comments_with_special_task_id(self, client, mock_db, monkeypatch):
        """Test listing comments with special characters in task_id."""
        mock_limit = Mock()
        mock_limit.stream = Mock(return_value=[])
        
        mock_order_by = Mock()
        mock_order_by.limit = Mock(return_value=mock_limit)
        
        mock_where = Mock()
        mock_where.order_by = Mock(return_value=mock_order_by)
        
        mock_collection = Mock()
        mock_collection.where = Mock(return_value=mock_where)
        
        mock_db.collection = Mock(return_value=mock_collection)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        special_task_id = "task-123_abc"
        response = client.get(f"/api/comments/by-task/{special_task_id}")
        
        assert response.status_code == 200
        # Verify the task_id was passed correctly to the query
        mock_collection.where.assert_called_once_with("task_id", "==", special_task_id)
    
    def test_add_comment_all_fields_present_in_response(self, client, mock_db, monkeypatch):
        """Test that all expected fields are present in the response."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment_complete"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": "Complete comment"
        }
        
        response = client.post("/api/comments", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        
        # Verify all expected fields are present
        expected_fields = ["comment_id", "task_id", "author_id", "body", "created_at", "edited_at"]
        for field in expected_fields:
            assert field in data, f"Field '{field}' missing from response"
