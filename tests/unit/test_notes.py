import sys
import os
from unittest.mock import Mock
import pytest
from datetime import datetime, timezone

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import notes_bp
from backend.api import notes as notes_module


# app, client, and mock_db fixtures provided by conftest.py


class TestNowIso:
    """Test the now_iso helper function."""
    
    def test_now_iso_returns_iso_format(self):
        """Test that now_iso returns a valid ISO format string."""
        result = notes_module.now_iso()
        
        # Verify it's a string
        assert isinstance(result, str)
        
        # Verify it can be parsed as ISO format
        parsed = datetime.fromisoformat(result.replace('Z', '+00:00'))
        assert isinstance(parsed, datetime)
    
    def test_now_iso_includes_timezone(self):
        """Test that now_iso includes timezone information."""
        result = notes_module.now_iso()
        
        # ISO format with timezone should contain '+' or 'Z'
        assert '+' in result or 'Z' in result.upper()
    
    def test_now_iso_uses_utc(self):
        """Test that now_iso uses UTC timezone."""
        result = notes_module.now_iso()
        
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
            "/api/notes",
            json=payload,
            content_type="application/json"
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.get_json()
        assert data["note_id"] == "comment123"
        assert data["task_id"] == "task1"
        assert data["author_id"] == "user1"
        assert data["body"] == "This is a test comment"
        assert "created_at" in data
        assert data["edited_at"] is None
        
        # Verify Firestore was called correctly
        mock_db.collection.assert_called_once_with("notes")
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
        
        response = client.post("/api/notes", json=payload)
        
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
        
        response = client.post("/api/notes", json=payload)
        
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
        
        response = client.post("/api/notes", json=payload)
        
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
        
        response = client.post("/api/notes", json=payload)
        
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
        
        response = client.post("/api/notes", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_add_comment_no_payload(self, client, mock_db, monkeypatch):
        """Test adding comment with no JSON payload."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post("/api/notes")
        
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
        
        response = client.post("/api/notes", json=payload)
        
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
        
        response = client.post("/api/notes", json=payload)
        
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
        
        response = client.get("/api/notes/by-task/task1")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify response
        assert len(data) == 2
        assert data[0]["note_id"] == "comment1"
        assert data[0]["body"] == "First comment"
        assert data[1]["note_id"] == "comment2"
        assert data[1]["body"] == "Second comment"
        
        # Verify Firestore query
        mock_db.collection.assert_called_once_with("notes")
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
        
        response = client.get("/api/notes/by-task/task999")
        
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
        
        response = client.get("/api/notes/by-task/task1")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["note_id"] == "comment_only"
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
        
        client.get("/api/notes/by-task/task1")
        
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
        
        client.get("/api/notes/by-task/task1")
        
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
        
        response = client.get("/api/notes/by-task/task1")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["edited_at"] == "2025-01-02T00:00:00+00:00"


class TestBlueprintRegistration:
    """Test that the blueprint is properly configured."""
    
    def test_blueprint_url_prefix(self):
        """Test that the blueprint has the correct URL prefix."""
        assert notes_bp.url_prefix == "/api/notes"
    
    def test_blueprint_name(self):
        """Test that the blueprint has the correct name."""
        assert notes_bp.name == "notes"


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
        
        response = client.post("/api/notes", json=payload)
        
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
        
        response = client.post("/api/notes", json=payload)
        
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
        
        response = client.post("/api/notes", json=payload)
        
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
        response = client.get(f"/api/notes/by-task/{special_task_id}")
        
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
        
        response = client.post("/api/notes", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        
        # Verify all expected fields are present
        expected_fields = ["note_id", "task_id", "author_id", "body", "created_at", "edited_at", "mentions"]
        for field in expected_fields:
            assert field in data, f"Field '{field}' missing from response"


class TestExtractMentions:
    """Test the _extract_mentions helper function."""
    
    def test_extract_single_mention(self):
        """Test extracting a single @mention."""
        body = "Hey @john, can you review this?"
        mentions = notes_module._extract_mentions(body)
        assert mentions == ["john"]
    
    def test_extract_multiple_mentions(self):
        """Test extracting multiple @mentions."""
        body = "CC @alice @bob and @charlie"
        mentions = notes_module._extract_mentions(body)
        # Result should be sorted for consistent comparison
        assert sorted(mentions) == ["alice", "bob", "charlie"]
    
    def test_extract_mentions_with_underscores_and_hyphens(self):
        """Test @mentions with underscores and hyphens."""
        body = "Notify @user_name and @test-user"
        mentions = notes_module._extract_mentions(body)
        assert sorted(mentions) == ["test-user", "user_name"]
    
    def test_extract_duplicate_mentions(self):
        """Test that duplicate @mentions are deduplicated."""
        body = "Hey @john, @john can you help?"
        mentions = notes_module._extract_mentions(body)
        assert mentions == ["john"]
    
    def test_extract_no_mentions(self):
        """Test extracting from text without @mentions."""
        body = "This is a regular comment"
        mentions = notes_module._extract_mentions(body)
        assert mentions == []
    
    def test_extract_empty_body(self):
        """Test extracting from empty body."""
        mentions = notes_module._extract_mentions("")
        assert mentions == []
    
    def test_extract_none_body(self):
        """Test extracting from None body."""
        mentions = notes_module._extract_mentions(None)
        assert mentions == []


class TestGetViewerId:
    """Test the _get_viewer_id helper function."""
    
    def test_get_viewer_from_header(self, app):
        """Test getting viewer ID from X-User-Id header."""
        with app.test_request_context(headers={"X-User-Id": "user123"}):
            viewer = notes_module._get_viewer_id()
            assert viewer == "user123"
    
    def test_get_viewer_from_query_param(self, app):
        """Test getting viewer ID from query parameter."""
        with app.test_request_context("/?viewer_id=user456"):
            viewer = notes_module._get_viewer_id()
            assert viewer == "user456"
    
    def test_header_takes_precedence(self, app):
        """Test that header takes precedence over query param."""
        with app.test_request_context(
            "/?viewer_id=query_user",
            headers={"X-User-Id": "header_user"}
        ):
            viewer = notes_module._get_viewer_id()
            assert viewer == "header_user"
    
    def test_no_viewer_returns_empty(self, app):
        """Test that missing viewer ID returns empty string."""
        with app.test_request_context():
            viewer = notes_module._get_viewer_id()
            assert viewer == ""
    
    def test_strips_whitespace(self, app):
        """Test that viewer ID is stripped of whitespace."""
        with app.test_request_context(headers={"X-User-Id": "  user789  "}):
            viewer = notes_module._get_viewer_id()
            assert viewer == "user789"


class TestUpdateComment:
    """Test the update_comment endpoint."""
    
    def test_update_comment_success(self, client, mock_db, monkeypatch):
        """Test successfully updating a comment."""
        # Mock Firestore
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict = Mock(return_value={
            "task_id": "task1",
            "author_id": "user1",
            "body": "Original comment",
            "mentions": [],
            "created_at": "2024-01-01T00:00:00Z",
            "edited_at": None
        })
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_doc)
        mock_doc_ref.update = Mock()
        
        # After update, return updated document
        updated_doc = Mock()
        updated_doc.to_dict = Mock(return_value={
            "task_id": "task1",
            "author_id": "user1",
            "body": "Updated comment with @alice",
            "mentions": ["alice"],
            "created_at": "2024-01-01T00:00:00Z",
            "edited_at": "2024-01-02T00:00:00Z"
        })
        mock_doc_ref.get = Mock(side_effect=[mock_doc, updated_doc])
        
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test data
        payload = {"body": "Updated comment with @alice"}
        
        response = client.patch(
            "/api/notes/comment123",
            json=payload,
            headers={"X-User-Id": "user1"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["note_id"] == "comment123"
        assert data["body"] == "Updated comment with @alice"
        assert "alice" in data["mentions"]
        assert data["edited_at"] is not None
        
        # Verify Firestore was called correctly
        mock_db.collection.assert_called_with("notes")
        mock_collection.document.assert_called_with("comment123")
        mock_doc_ref.update.assert_called_once()
    
    def test_update_comment_not_found(self, client, mock_db, monkeypatch):
        """Test updating a non-existent comment."""
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_doc)
        
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {"body": "Updated comment"}
        
        response = client.patch(
            "/api/notes/nonexistent",
            json=payload,
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()
    
    def test_update_comment_unauthorized(self, client, mock_db, monkeypatch):
        """Test updating someone else's comment."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict = Mock(return_value={
            "task_id": "task1",
            "author_id": "user1",
            "body": "Original comment",
            "mentions": [],
            "created_at": "2024-01-01T00:00:00Z",
            "edited_at": None
        })
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_doc)
        
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {"body": "Trying to update"}
        
        response = client.patch(
            "/api/notes/comment123",
            json=payload,
            headers={"X-User-Id": "user2"}  # Different user
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert "own notes" in data["error"].lower()
    
    def test_update_comment_no_auth(self, client, mock_db, monkeypatch):
        """Test updating comment without authentication."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {"body": "Updated comment"}
        
        response = client.patch("/api/notes/comment123", json=payload)
        
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "authentication" in data["error"].lower()
    
    def test_update_comment_missing_body(self, client, mock_db, monkeypatch):
        """Test updating comment without body."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict = Mock(return_value={
            "author_id": "user1",
            "body": "Original"
        })
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_doc)
        
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.patch(
            "/api/notes/comment123",
            json={},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "body" in data["error"].lower()
    
    def test_update_comment_empty_body(self, client, mock_db, monkeypatch):
        """Test updating comment with empty body."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict = Mock(return_value={
            "author_id": "user1",
            "body": "Original"
        })
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_doc)
        
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.patch(
            "/api/notes/comment123",
            json={"body": "   "},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestDeleteComment:
    """Test the delete_comment endpoint."""
    
    def test_delete_comment_success(self, client, mock_db, monkeypatch):
        """Test successfully deleting a comment."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict = Mock(return_value={
            "task_id": "task1",
            "author_id": "user1",
            "body": "Comment to delete",
            "mentions": [],
            "created_at": "2024-01-01T00:00:00Z"
        })
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_doc)
        mock_doc_ref.delete = Mock()
        
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/notes/comment123",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "deleted" in data["message"].lower()
        
        # Verify Firestore delete was called
        mock_doc_ref.delete.assert_called_once()
    
    def test_delete_comment_not_found(self, client, mock_db, monkeypatch):
        """Test deleting a non-existent comment."""
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_doc)
        
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/notes/nonexistent",
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()
    
    def test_delete_comment_unauthorized(self, client, mock_db, monkeypatch):
        """Test deleting someone else's comment."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict = Mock(return_value={
            "task_id": "task1",
            "author_id": "user1",
            "body": "Someone's comment",
            "mentions": []
        })
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_doc)
        
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/notes/comment123",
            headers={"X-User-Id": "user2"}  # Different user
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert "own notes" in data["error"].lower()
    
    def test_delete_comment_no_auth(self, client, mock_db, monkeypatch):
        """Test deleting comment without authentication."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete("/api/notes/comment123")
        
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "authentication" in data["error"].lower()


class TestAddCommentWithMentions:
    """Test adding comments with @mentions."""
    
    def test_add_comment_with_single_mention(self, client, mock_db, monkeypatch):
        """Test adding a comment with a single @mention."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment123"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": "Hey @john, can you review this?"
        }
        
        response = client.post("/api/notes", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert "mentions" in data
        assert "john" in data["mentions"]
    
    def test_add_comment_with_multiple_mentions(self, client, mock_db, monkeypatch):
        """Test adding a comment with multiple @mentions."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment123"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": "CC @alice @bob and @charlie on this"
        }
        
        response = client.post("/api/notes", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert "mentions" in data
        assert "alice" in data["mentions"]
        assert "bob" in data["mentions"]
        assert "charlie" in data["mentions"]
    
    def test_add_comment_no_mentions(self, client, mock_db, monkeypatch):
        """Test adding a comment without @mentions."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "comment123"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task1",
            "author_id": "user1",
            "body": "Regular comment without mentions"
        }
        
        response = client.post("/api/notes", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert "mentions" in data
        assert data["mentions"] == []

