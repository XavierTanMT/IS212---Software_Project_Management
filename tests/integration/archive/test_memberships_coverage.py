"""
Integration tests to achieve 100% coverage for memberships.py
Covers missing lines: 8, 12-22
"""

from datetime import datetime, timezone
import pytest


class TestMembershipsFullCoverage:
    """Test memberships.py for 100% coverage."""
    
    def test_add_member_success(self, client, db):
        """Test POST /api/memberships - successful member addition (lines 12-22)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        project_id = f"proj_{timestamp}"
        user_id = f"user_{timestamp}"
        
        # Create project and user
        db.collection("projects").document(project_id).set({
            "name": "Test Project",
            "handle": f"proj{timestamp}",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "Test User"
        })
        
        try:
            # Add member with explicit role
            response = client.post("/api/memberships", json={
                "project_id": project_id,
                "user_id": user_id,
                "role": "developer"
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert data["project_id"] == project_id
            assert data["user_id"] == user_id
            assert data["role"] == "developer"
            assert "added_at" in data  # This covers line 8 (now_iso call)
            
            # Verify in Firestore
            mem_id = f"{project_id}_{user_id}"
            doc = db.collection("memberships").document(mem_id).get()
            assert doc.exists
            assert doc.to_dict()["role"] == "developer"
            
            # Cleanup membership
            db.collection("memberships").document(mem_id).delete()
        finally:
            db.collection("projects").document(project_id).delete()
            db.collection("users").document(user_id).delete()
    
    def test_add_member_default_role(self, client, db):
        """Test POST /api/memberships - default role is 'contributor' (line 16)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        project_id = f"proj_{timestamp}"
        user_id = f"user_{timestamp}"
        
        db.collection("projects").document(project_id).set({
            "name": "Test Project",
            "handle": f"proj{timestamp}",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "Test User"
        })
        
        try:
            # Add member without specifying role
            response = client.post("/api/memberships", json={
                "project_id": project_id,
                "user_id": user_id
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert data["role"] == "contributor"  # Default role
            
            # Cleanup
            mem_id = f"{project_id}_{user_id}"
            db.collection("memberships").document(mem_id).delete()
        finally:
            db.collection("projects").document(project_id).delete()
            db.collection("users").document(user_id).delete()
    
    def test_add_member_missing_project_id(self, client, db):
        """Test POST /api/memberships - missing project_id (line 18)."""
        response = client.post("/api/memberships", json={
            "user_id": "user123",
            "role": "developer"
        })
        
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
    
    def test_add_member_missing_user_id(self, client, db):
        """Test POST /api/memberships - missing user_id (line 18)."""
        response = client.post("/api/memberships", json={
            "project_id": "proj123",
            "role": "developer"
        })
        
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
    
    def test_add_member_empty_strings(self, client, db):
        """Test POST /api/memberships - empty strings after strip (line 18)."""
        response = client.post("/api/memberships", json={
            "project_id": "   ",
            "user_id": "   ",
            "role": "developer"
        })
        
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
    
    def test_add_member_updates_existing(self, client, db):
        """Test POST /api/memberships - can update existing membership (line 20-22)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        project_id = f"proj_{timestamp}"
        user_id = f"user_{timestamp}"
        
        db.collection("projects").document(project_id).set({
            "name": "Test Project",
            "handle": f"proj{timestamp}",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        db.collection("users").document(user_id).set({
            "email": f"{user_id}@example.com",
            "name": "Test User"
        })
        
        # Pre-create membership
        mem_id = f"{project_id}_{user_id}"
        db.collection("memberships").document(mem_id).set({
            "project_id": project_id,
            "user_id": user_id,
            "role": "viewer",
            "added_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # Update membership with new role
            response = client.post("/api/memberships", json={
                "project_id": project_id,
                "user_id": user_id,
                "role": "admin"
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert data["role"] == "admin"
            
            # Verify update in Firestore
            doc = db.collection("memberships").document(mem_id).get()
            assert doc.to_dict()["role"] == "admin"
            
            # Cleanup
            db.collection("memberships").document(mem_id).delete()
        finally:
            db.collection("projects").document(project_id).delete()
            db.collection("users").document(user_id).delete()
    
    def test_list_members_empty_project(self, client, db):
        """Test GET /api/memberships/by-project/<id> - empty project (line 26-29)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        project_id = f"empty_proj_{timestamp}"
        
        # Don't create any memberships
        response = client.get(f"/api/memberships/by-project/{project_id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_members_multiple(self, client, db):
        """Test GET /api/memberships/by-project/<id> - multiple members."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        project_id = f"proj_{timestamp}"
        
        db.collection("projects").document(project_id).set({
            "name": "Multi Member Project",
            "handle": f"proj{timestamp}",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create multiple memberships
        members = []
        for i in range(3):
            user_id = f"user{i}_{timestamp}"
            mem_id = f"{project_id}_{user_id}"
            
            db.collection("users").document(user_id).set({
                "email": f"{user_id}@example.com",
                "name": f"User {i}"
            })
            
            db.collection("memberships").document(mem_id).set({
                "project_id": project_id,
                "user_id": user_id,
                "role": f"role{i}",
                "added_at": datetime.now(timezone.utc).isoformat()
            })
            
            members.append((user_id, mem_id))
        
        try:
            response = client.get(f"/api/memberships/by-project/{project_id}")
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 3
            
            # Verify all members present
            user_ids = [m["user_id"] for m in data]
            for user_id, _ in members:
                assert user_id in user_ids
        finally:
            db.collection("projects").document(project_id).delete()
            for user_id, mem_id in members:
                db.collection("users").document(user_id).delete()
                db.collection("memberships").document(mem_id).delete()
