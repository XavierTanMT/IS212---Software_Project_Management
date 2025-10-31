"""
Final coverage boost tests to reach 100% for projects.py and notes.py.

These tests target the last remaining untested lines to achieve complete coverage.
"""

import pytest
from datetime import datetime, timezone
import uuid
# Import the private function to test defensive code path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from backend.api.notes import _extract_mentions


class TestProjectsFinalCoverage:
    """Tests to reach 100% coverage for projects.py"""

    def test_create_project_with_key(self, client, db):
        """Test creating project with a key field - covers line 52-53"""
        # Create a user first
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "email": f"{user_id}@test.com",
            "handle": f"handle_{user_id}",
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create project with key
        response = client.post("/api/projects", json={
            "name": "Test Project With Key",
            "key": "TPK",
            "owner_id": user_id,
            "description": "Test project with key field"
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Test Project With Key"
        assert data["key"] == "TPK"
        assert data["owner_id"] == user_id
        
        # Cleanup
        db.collection("projects").document(data["project_id"]).delete()
        mem_id = f"{data['project_id']}_{user_id}"
        db.collection("memberships").document(mem_id).delete()
        db.collection("users").document(user_id).delete()

    def test_create_project_without_key(self, client, db):
        """Test creating project without key - key should be None"""
        # Create a user first
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "email": f"{user_id}@test.com",
            "handle": f"handle_{user_id}",
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create project without key
        response = client.post("/api/projects", json={
            "name": "Test Project No Key",
            "owner_id": user_id,
            "description": "Test project without key"
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Test Project No Key"
        assert data["key"] is None
        assert data["owner_id"] == user_id
        
        # Cleanup
        db.collection("projects").document(data["project_id"]).delete()
        mem_id = f"{data['project_id']}_{user_id}"
        db.collection("memberships").document(mem_id).delete()
        db.collection("users").document(user_id).delete()

    def test_create_project_with_empty_key(self, client, db):
        """Test creating project with empty string key - should become None"""
        # Create a user first
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "email": f"{user_id}@test.com",
            "handle": f"handle_{user_id}",
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create project with empty key
        response = client.post("/api/projects", json={
            "name": "Test Project Empty Key",
            "key": "",
            "owner_id": user_id
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Test Project Empty Key"
        assert data["key"] is None  # Empty string becomes None
        
        # Cleanup
        db.collection("projects").document(data["project_id"]).delete()
        mem_id = f"{data['project_id']}_{user_id}"
        db.collection("memberships").document(mem_id).delete()
        db.collection("users").document(user_id).delete()

    def test_create_project_with_description_none(self, client, db):
        """Test creating project without description - should be None"""
        # Create a user first
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "email": f"{user_id}@test.com",
            "handle": f"handle_{user_id}",
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create project without description
        response = client.post("/api/projects", json={
            "name": "Test Project No Desc",
            "owner_id": user_id
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["description"] is None
        
        # Cleanup
        db.collection("projects").document(data["project_id"]).delete()
        mem_id = f"{data['project_id']}_{user_id}"
        db.collection("memberships").document(mem_id).delete()
        db.collection("users").document(user_id).delete()

    def test_create_project_owner_resolved_by_handle(self, client, db):
        """Test owner resolution triggers exception path - covers lines 42-43"""
        # Use a handle that will cause the Firestore query to potentially have issues
        # The exception handler (lines 42-43) catches any errors during resolution
        fake_handle = f"nonexistent_{uuid.uuid4().hex[:8]}"
        
        # Create project with non-existent handle
        # The code will try to resolve it, fail, and use it as-is
        response = client.post("/api/projects", json={
            "name": "Test Project Exception",
            "owner_id": fake_handle,  # Non-existent handle
            "description": "Testing exception handling"
        })
        
        assert response.status_code == 201
        data = response.get_json()
        # The handle couldn't be resolved, so it's used as the owner_id
        assert data["owner_id"] == fake_handle
        assert data["name"] == "Test Project Exception"
        
        # Cleanup
        db.collection("projects").document(data["project_id"]).delete()
        mem_id = f"{data['project_id']}_{fake_handle}"
        db.collection("memberships").document(mem_id).delete()

    def test_create_project_with_whitespace_only_fields(self, client, db):
        """Test creating project with whitespace-only fields after strip()"""
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "email": f"{user_id}@test.com",
            "handle": f"handle_{user_id}",
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create project with whitespace in key and description
        response = client.post("/api/projects", json={
            "name": "Test Project",
            "key": "   ",  # Whitespace only - becomes None after strip()
            "owner_id": user_id,
            "description": "   "  # Whitespace only - becomes None after strip()
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["key"] is None  # Whitespace stripped to empty, then None
        assert data["description"] is None
        
        # Cleanup
        db.collection("projects").document(data["project_id"]).delete()
        mem_id = f"{data['project_id']}_{user_id}"
        db.collection("memberships").document(mem_id).delete()
        db.collection("users").document(user_id).delete()

    def test_create_project_owner_resolved_by_email_with_at(self, client, db):
        """Test owner resolution by email"""
        # Create a user with email
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        email = f"testuser{uuid.uuid4().hex[:8]}@example.com"
        
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "email": email.lower(),  # Store lowercase
            "handle": f"handle_{user_id}",
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create project using email as owner_id (should resolve to user_id)
        response = client.post("/api/projects", json={
            "name": "Test Project By Email",
            "owner_id": email,  # Use email with @ symbol
        })
        
        assert response.status_code == 201
        data = response.get_json()
        # The email should be resolved to the actual user_id
        assert data["owner_id"] == user_id
        assert data["name"] == "Test Project By Email"
        
        # Cleanup
        db.collection("projects").document(data["project_id"]).delete()
        mem_id = f"{data['project_id']}_{user_id}"
        db.collection("memberships").document(mem_id).delete()
        db.collection("users").document(user_id).delete()


class TestNotesFinalCoverage:
    """Tests to reach 100% coverage for notes.py"""

    def test_extract_mentions_with_none_directly(self):
        """Test _extract_mentions directly with None - covers line 19"""
        # This tests the defensive code path that can't be reached through the API
        result = _extract_mentions(None)
        assert result == []
    
    def test_extract_mentions_with_empty_string_directly(self):
        """Test _extract_mentions directly with empty string - covers line 19"""
        result = _extract_mentions("")
        assert result == []
    
    def test_extract_mentions_with_whitespace_directly(self):
        """Test _extract_mentions directly with whitespace - covers line 19"""
        result = _extract_mentions("   ")
        assert result == []

    def test_extract_mentions_empty_string(self, client, db):
        """Test _extract_mentions with empty string body - covers line 19 (return [])"""
        # Create task
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Test Task",
            "status": "todo",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        author_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # The validation will catch empty body after strip()
        # This triggers the if not body check in _extract_mentions via validation
        response = client.post("/api/notes", json={
            "task_id": task_id,
            "author_id": author_id,
            "body": ""  # Empty string - after strip() becomes falsy
        })
        
        # Should fail validation because body is required
        assert response.status_code == 400
        
        # Cleanup
        db.collection("tasks").document(task_id).delete()
    
    def test_add_note_no_mentions(self, client, db):
        """Test adding note without any @mentions - covers line 19 (return [])"""
        # Create task
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Test Task",
            "status": "todo",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        author_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Create note without any mentions
        response = client.post("/api/notes", json={
            "task_id": task_id,
            "author_id": author_id,
            "body": "This is a note with no mentions at all"
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert "mentions" in data
        # Should have empty list when no mentions
        assert len(data["mentions"]) == 0
        assert data["mentions"] == []
        
        # Cleanup
        db.collection("notes").document(data["note_id"]).delete()
        db.collection("tasks").document(task_id).delete()

    def test_add_note_with_mentions(self, client, db):
        """Test adding note with @mentions to ensure mentions are extracted"""
        # Create task
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        db.collection("tasks").document(task_id).set({
            "task_id": task_id,
            "title": "Test Task",
            "status": "todo",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        author_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Create note with mentions
        response = client.post("/api/notes", json={
            "task_id": task_id,
            "author_id": author_id,
            "body": "Hey @john and @jane, please review this task @alice"
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert "mentions" in data
        # Should have 3 unique mentions
        assert len(data["mentions"]) == 3
        assert "john" in data["mentions"]
        assert "jane" in data["mentions"]
        assert "alice" in data["mentions"]
        
        # Cleanup
        db.collection("notes").document(data["note_id"]).delete()
        db.collection("tasks").document(task_id).delete()

    def test_list_notes_empty_result(self, client, db):
        """Test listing notes for task with no notes"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        response = client.get(f"/api/notes/by-task/{task_id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0
