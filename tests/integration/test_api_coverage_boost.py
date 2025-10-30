"""
Integration tests to boost API coverage.
Focuses on testing endpoints and code paths with low coverage.
"""

from datetime import datetime, timezone, timedelta
import pytest


class TestAdminEndpoints:
    """Test admin endpoints - currently 11% coverage."""
    
    def test_admin_check_user(self, client, db):
        """Test GET /api/users/admin/check/<user_id> - check user sync status."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        admin_id = f"admin_{timestamp}"
        
        # Create admin user
        db.collection("users").document(admin_id).set({
            "email": f"{admin_id}@example.com",
            "name": "Admin User",
            "role": "admin"
        })
        
        try:
            response = client.get(f"/api/users/admin/check/{admin_id}")
            
            assert response.status_code == 200
            data = response.get_json()
            # Admin check endpoint returns sync status
            assert "in_firestore" in data
            assert "in_firebase_auth" in data
            assert data["in_firestore"] == True
        finally:
            db.collection("users").document(admin_id).delete()
    
    def test_admin_cleanup_user(self, client, db):
        """Test DELETE /api/users/admin/cleanup/<user_id> - requires confirmation."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        user_id = f"cleanup_{timestamp}"
        
        # Create user with associated data
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "User to Cleanup"
        })
        
        # Create a task for the user
        task_id = f"task_{timestamp}"
        db.collection("tasks").document(task_id).set({
            "title": "Test Task",
            "description": "Will be cleaned",
            "status": "To Do",
            "priority": 5,
            "created_by": {"user_id": user_id, "name": "User to Cleanup"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # Test without confirmation - should fail
            response = client.delete(f"/api/users/admin/cleanup/{user_id}")
            assert response.status_code == 400
            data = response.get_json()
            assert "confirm" in data["error"].lower() or "confirmation" in data["error"].lower()
        finally:
            # Cleanup
            db.collection("users").document(user_id).delete()
            db.collection("tasks").document(task_id).delete()
    
    def test_admin_sync_user(self, client, db):
        """Test POST /api/users/admin/sync/<user_id> - requires password parameter."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        user_id = f"sync_{timestamp}"
        
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "Sync User"
        })
        
        try:
            # Test without password - should fail with 400
            response = client.post(f"/api/users/admin/sync/{user_id}", json={})
            assert response.status_code == 400
            data = response.get_json()
            assert "password" in data.get("error", "").lower()
        finally:
            db.collection("users").document(user_id).delete()


class TestAuthEndpoints:
    """Test auth endpoints - currently 12% coverage."""
    
    def test_auth_verify_token(self, client, db):
        """Test POST /api/users/auth/verify - requires firebase_token field."""
        # Test without firebase_token field - should fail
        response = client.post("/api/users/auth/verify", json={"token": "test_token"})
        assert response.status_code == 400
        data = response.get_json()
        assert "firebase" in data.get("error", "").lower() and "token" in data.get("error", "").lower()


class TestDashboardEndpoints:
    """Test dashboard endpoints - currently 27% coverage."""
    
    def test_get_user_dashboard_empty(self, client, db):
        """Test GET /api/users/<user_id>/dashboard with no tasks."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        user_id = f"dash_{timestamp}"
        
        # Create user only, no tasks
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "Dashboard User"
        })
        
        try:
            # The correct full path is /api + /users/<user_id>/dashboard
            response = client.get(f"/api/users/{user_id}/dashboard")
            
            assert response.status_code == 200
            data = response.get_json()
            # Dashboard should return some structure even if empty
            assert isinstance(data, dict)
        finally:
            db.collection("users").document(user_id).delete()


class TestAttachmentsEndpoints:
    """Test attachments endpoints - currently 37% coverage."""
    
    def test_list_task_attachments_empty(self, client, db):
        """Test GET /api/attachments/by-task/<task_id> with no attachments."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        task_id = f"task_noattach_{timestamp}"
        
        # Test the endpoint with no attachments
        # The endpoint now falls back to unordered query if composite index doesn't exist
        response = client.get(f"/api/attachments/by-task/{task_id}")
        
        # Should return empty list
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0



class TestMembershipsEndpoints:
    """Test memberships endpoints - currently 38% coverage."""
    
    def test_list_project_members(self, client, db):
        """Test GET /api/memberships/by-project/<project_id>."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        project_id = f"proj_{timestamp}"
        user_id = f"user_{timestamp}"
        
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "User"
        })
        
        db.collection("projects").document(project_id).set({
            "name": "Project",
            "handle": f"proj{timestamp}",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        mem_id = f"{project_id}_{user_id}"
        db.collection("memberships").document(mem_id).set({
            "project_id": project_id,
            "user_id": user_id,
            "role": "owner"
        })
        
        try:
            response = client.get(f"/api/memberships/by-project/{project_id}")
            
            assert response.status_code == 200
            data = response.get_json()
            # The endpoint returns an array directly, not wrapped in {"members": [...]}
            assert isinstance(data, list)
            assert len(data) >= 1
            assert data[0]["project_id"] == project_id
        finally:
            db.collection("users").document(user_id).delete()
            db.collection("projects").document(project_id).delete()
            db.collection("memberships").document(mem_id).delete()


class TestNotesEndpoints:
    """Test notes endpoints - currently 49% coverage."""
    
    def test_list_task_notes(self, client, db):
        """Test GET /api/notes/by-task/<task_id>."""
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
            "description": "Test",
            "status": "To Do",
            "priority": 5,
            "created_by": {"user_id": user_id, "name": "User"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        db.collection("notes").document(note_id).set({
            "task_id": task_id,
            "author_id": user_id,
            "body": "Test comment",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            response = client.get(f"/api/notes/by-task/{task_id}")
            
            assert response.status_code == 200
            data = response.get_json()
            # The endpoint returns an array directly, not wrapped
            assert isinstance(data, list)
            assert len(data) >= 1
            assert data[0]["task_id"] == task_id
        finally:
            db.collection("users").document(user_id).delete()
            db.collection("tasks").document(task_id).delete()
            db.collection("notes").document(note_id).delete()
    
    def test_update_note(self, client, db):
        """Test PATCH /api/notes/<note_id> - update note."""
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
            "description": "Test",
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
                json={"body": "Updated content"}
            )
            
            assert response.status_code == 200
            
            # Verify update
            doc = db.collection("notes").document(note_id).get()
            assert doc.to_dict()["body"] == "Updated content"
        finally:
            db.collection("users").document(user_id).delete()
            db.collection("tasks").document(task_id).delete()
            db.collection("notes").document(note_id).delete()
    
    def test_delete_note(self, client, db):
        """Test DELETE /api/notes/<note_id> - delete note."""
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
            "description": "Test",
            "status": "To Do",
            "priority": 5,
            "created_by": {"user_id": user_id, "name": "User"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        db.collection("notes").document(note_id).set({
            "task_id": task_id,
            "author_id": user_id,
            "body": "To be deleted",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            response = client.delete(
                f"/api/notes/{note_id}",
                headers={"X-User-Id": user_id}
            )
            
            assert response.status_code in [200, 204]
            
            # Verify deletion
            doc = db.collection("notes").document(note_id).get()
            assert not doc.exists
        finally:
            db.collection("users").document(user_id).delete()
            db.collection("tasks").document(task_id).delete()


class TestProjectEndpoints:
    """Test project endpoints - currently 50% coverage."""
    
    def test_update_project(self, client, db):
        """Test PATCH /api/projects/<project_id> - update project."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        project_id = f"proj_{timestamp}"
        user_id = f"user_{timestamp}"
        
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "Owner"
        })
        
        db.collection("projects").document(project_id).set({
            "name": "Original Name",
            "description": "Original Description",
            "handle": f"proj{timestamp}",
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            response = client.patch(
                f"/api/projects/{project_id}",
                headers={"X-User-Id": user_id},
                json={
                    "name": "Updated Name",
                    "description": "Updated Description"
                }
            )
            
            assert response.status_code == 200
            
            # Verify update
            doc = db.collection("projects").document(project_id).get()
            data = doc.to_dict()
            assert data["name"] == "Updated Name"
            assert data["description"] == "Updated Description"
        finally:
            db.collection("users").document(user_id).delete()
            db.collection("projects").document(project_id).delete()


class TestUserEndpoints:
    """Test user endpoints - currently 87% coverage (good but can improve)."""
    
    def test_get_user_role(self, client, db):
        """Test GET /api/users/<user_id>/role - get user role."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        user_id = f"role_user_{timestamp}"
        
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "Role User",
            "role": "manager"
        })
        
        try:
            response = client.get(f"/api/users/{user_id}/role")
            
            assert response.status_code == 200
            data = response.get_json()
            assert "role" in data
            assert data["role"] == "manager"
        finally:
            db.collection("users").document(user_id).delete()
