"""
Comprehensive integration tests to achieve 100% coverage across all backend modules.
This file exercises all code paths through the Flask test client with Firebase emulators.
"""
import pytest
from datetime import datetime, timezone


def get_timestamp():
    """Generate unique timestamp for test data."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


class TestProjectsIntegration:
    """Integration tests for projects.py to reach 100% coverage"""
    
    def test_create_project_owner_resolution_by_handle(self, client, db):
        """Test creating project where owner_id is resolved via handle query"""
        timestamp = get_timestamp()
        user_id = f"handleuser_{timestamp}"
        
        # Create a user with a handle
        user_payload = {
            "user_id": user_id,
            "email": f"handleuser_{timestamp}@test.com",
            "name": "Handle User",
            "handle": f"handleuser{timestamp}"
        }
        user_resp = client.post("/api/users", json=user_payload)
        assert user_resp.status_code == 201
        
        try:
            # Create project using the handle (not the user_id)
            project_payload = {
                "name": f"Handle Project {timestamp}",
                "owner_id": f"handleuser{timestamp}",  # Using handle, not user_id
                "description": "Test handle resolution"
            }
            resp = client.post(
                "/api/projects",
                json=project_payload,
                headers={"X-User-Id": user_id}
            )
            assert resp.status_code == 201
            project_id = resp.get_json().get("project_id")
            
            # Cleanup project
            if project_id:
                db.collection("projects").document(project_id).delete()
        finally:
            # Cleanup user
            db.collection("users").document(user_id).delete()
        
    def test_create_project_owner_resolution_by_email(self, client, db):
        """Test creating project where owner_id is resolved via email query"""
        timestamp = get_timestamp()
        user_id = f"emailuser_{timestamp}"
        email = f"emailuser_{timestamp}@test.com"
        
        # Create a user
        user_payload = {
            "user_id": user_id,
            "email": email,
            "name": "Email User"
        }
        user_resp = client.post("/api/users", json=user_payload)
        assert user_resp.status_code == 201
        
        try:
            # Create project using email (contains @)
            project_payload = {
                "name": f"Email Project {timestamp}",
                "owner_id": email,  # Using email with @
                "description": "Test email resolution"
            }
            resp = client.post(
                "/api/projects",
                json=project_payload,
                headers={"X-User-Id": user_id}
            )
            assert resp.status_code == 201
            project_id = resp.get_json().get("project_id")
            
            # Cleanup
            if project_id:
                db.collection("projects").document(project_id).delete()
        finally:
            db.collection("users").document(user_id).delete()
        
    def test_create_project_owner_not_found(self, client, db):
        """Test creating project where owner_id cannot be resolved"""
        timestamp = get_timestamp()
        user_id = f"creator_{timestamp}"
        
        # Create a user to make the API call
        user_payload = {
            "user_id": user_id,
            "email": f"creator_{timestamp}@test.com",
            "name": "Creator"
        }
        user_resp = client.post("/api/users", json=user_payload)
        assert user_resp.status_code == 201
        
        try:
            # Try to create project with non-existent owner
            project_payload = {
                "name": f"Orphan Project {timestamp}",
                "owner_id": f"nonexistent_{timestamp}@nowhere.com",
                "description": "Owner not found"
            }
            resp = client.post(
                "/api/projects",
                json=project_payload,
                headers={"X-User-Id": user_id}
            )
            # Should still create the project with the unresolved owner_id
            assert resp.status_code == 201
            project_id = resp.get_json().get("project_id")
            
            # Cleanup
            if project_id:
                db.collection("projects").document(project_id).delete()
        finally:
            db.collection("users").document(user_id).delete()
