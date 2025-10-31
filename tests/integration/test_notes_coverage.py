"""
Integration tests to achieve 100% coverage for notes.py
Covers missing lines: 19, 34, 66, 73, 79, 85, 109, 116, 122
"""

from datetime import datetime, timezone
import pytest


class TestNotesErrorHandling:
    """Test error handling paths in notes.py for 100% coverage."""
    
    def test_add_note_missing_fields(self, client, db):
        """Test POST /api/notes - missing required fields (line 34)."""
        # Missing task_id
        response = client.post("/api/notes", json={"author_id": "user1", "body": "test"})
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
        
        # Missing author_id
        response = client.post("/api/notes", json={"task_id": "task1", "body": "test"})
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
        
        # Missing body
        response = client.post("/api/notes", json={"task_id": "task1", "author_id": "user1"})
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
    
    def test_extract_mentions_with_empty_body(self, client, db):
        """Test mention extraction with empty/None body (line 19)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        task_id = f"task_{timestamp}"
        user_id = f"user_{timestamp}"
        
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "User"
        })
        
        db.collection("tasks").document(task_id).set({
            "title": "Task",
            "status": "To Do",
            "priority": 5,
            "created_by": {"user_id": user_id, "name": "User"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # Test with body containing mentions
            response = client.post("/api/notes", json={
                "task_id": task_id,
                "author_id": user_id,
                "body": "Hello @john and @jane_doe"
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert "mentions" in data
            assert len(data["mentions"]) == 2
            assert set(data["mentions"]) == {"john", "jane_doe"}
            
            # Cleanup
            if "note_id" in data:
                db.collection("notes").document(data["note_id"]).delete()
        finally:
            db.collection("users").document(user_id).delete()
            db.collection("tasks").document(task_id).delete()
    
    def test_update_note_no_authentication(self, client, db):
        """Test PATCH /api/notes/<note_id> - no authentication (line 66)."""
        response = client.patch("/api/notes/fake_note_id", json={"body": "updated"})
        assert response.status_code == 401
        assert "authentication" in response.get_json()["error"].lower()
    
    def test_update_note_not_found(self, client, db):
        """Test PATCH /api/notes/<note_id> - note not found (line 73)."""
        response = client.patch(
            "/api/notes/nonexistent_note",
            headers={"X-User-Id": "user1"},
            json={"body": "updated"}
        )
        assert response.status_code == 404
        assert "not found" in response.get_json()["error"].lower()
    
    def test_update_note_wrong_author(self, client, db):
        """Test PATCH /api/notes/<note_id> - wrong author (line 79)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        task_id = f"task_{timestamp}"
        author_id = f"author_{timestamp}"
        other_id = f"other_{timestamp}"
        note_id = f"note_{timestamp}"
        
        db.collection("users").document(author_id).set({
            "email": f"{author_id}@example.com",
            "name": "Author"
        })
        
        db.collection("users").document(other_id).set({
            "email": f"{other_id}@example.com",
            "name": "Other"
        })
        
        db.collection("tasks").document(task_id).set({
            "title": "Task",
            "status": "To Do",
            "priority": 5,
            "created_by": {"user_id": author_id, "name": "Author"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        db.collection("notes").document(note_id).set({
            "task_id": task_id,
            "author_id": author_id,
            "body": "Original content",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # Try to update as different user
            response = client.patch(
                f"/api/notes/{note_id}",
                headers={"X-User-Id": other_id},
                json={"body": "Hacked content"}
            )
            
            assert response.status_code == 403
            assert "your own" in response.get_json()["error"].lower()
        finally:
            db.collection("users").document(author_id).delete()
            db.collection("users").document(other_id).delete()
            db.collection("tasks").document(task_id).delete()
            db.collection("notes").document(note_id).delete()
    
    def test_update_note_empty_body(self, client, db):
        """Test PATCH /api/notes/<note_id> - empty body (line 85)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        task_id = f"task_{timestamp}"
        user_id = f"user_{timestamp}"
        note_id = f"note_{timestamp}"
        
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "User"
        })
        
        db.collection("tasks").document(task_id).set({
            "title": "Task",
            "status": "To Do",
            "priority": 5,
            "created_by": {"user_id": user_id, "name": "User"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        db.collection("notes").document(note_id).set({
            "task_id": task_id,
            "author_id": user_id,
            "body": "Original content",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            response = client.patch(
                f"/api/notes/{note_id}",
                headers={"X-User-Id": user_id},
                json={"body": ""}
            )
            
            assert response.status_code == 400
            assert "required" in response.get_json()["error"].lower()
        finally:
            db.collection("users").document(user_id).delete()
            db.collection("tasks").document(task_id).delete()
            db.collection("notes").document(note_id).delete()
    
    def test_delete_note_no_authentication(self, client, db):
        """Test DELETE /api/notes/<note_id> - no authentication (line 109)."""
        response = client.delete("/api/notes/fake_note_id")
        assert response.status_code == 401
        assert "authentication" in response.get_json()["error"].lower()
    
    def test_delete_note_not_found(self, client, db):
        """Test DELETE /api/notes/<note_id> - note not found (line 116)."""
        response = client.delete(
            "/api/notes/nonexistent_note",
            headers={"X-User-Id": "user1"}
        )
        assert response.status_code == 404
        assert "not found" in response.get_json()["error"].lower()
    
    def test_delete_note_wrong_author(self, client, db):
        """Test DELETE /api/notes/<note_id> - wrong author (line 122)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        task_id = f"task_{timestamp}"
        author_id = f"author_{timestamp}"
        other_id = f"other_{timestamp}"
        note_id = f"note_{timestamp}"
        
        db.collection("users").document(author_id).set({
            "email": f"{author_id}@example.com",
            "name": "Author"
        })
        
        db.collection("users").document(other_id).set({
            "email": f"{other_id}@example.com",
            "name": "Other"
        })
        
        db.collection("tasks").document(task_id).set({
            "title": "Task",
            "status": "To Do",
            "priority": 5,
            "created_by": {"user_id": author_id, "name": "Author"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        db.collection("notes").document(note_id).set({
            "task_id": task_id,
            "author_id": author_id,
            "body": "Content",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # Try to delete as different user
            response = client.delete(
                f"/api/notes/{note_id}",
                headers={"X-User-Id": other_id}
            )
            
            assert response.status_code == 403
            assert "your own" in response.get_json()["error"].lower()
            
            # Verify note still exists
            doc = db.collection("notes").document(note_id).get()
            assert doc.exists
        finally:
            db.collection("users").document(author_id).delete()
            db.collection("users").document(other_id).delete()
            db.collection("tasks").document(task_id).delete()
            db.collection("notes").document(note_id).delete()
