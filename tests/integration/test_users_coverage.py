"""
Integration tests to achieve 100% coverage for users.py
Covers missing lines: 15, 27, 31, 34, 50, 58
"""

from datetime import datetime, timezone
import pytest


class TestUsersErrorHandling:
    """Test error handling paths in users.py for 100% coverage."""
    
    def test_create_user_missing_fields(self, client, db):
        """Test POST /api/users - missing required fields (line 27)."""
        # Missing user_id
        response = client.post("/api/users", json={"name": "Test", "email": "test@example.com"})
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
        
        # Missing name
        response = client.post("/api/users", json={"user_id": "user1", "email": "test@example.com"})
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
        
        # Missing email
        response = client.post("/api/users", json={"user_id": "user1", "name": "Test"})
        assert response.status_code == 400
        assert "required" in response.get_json()["error"].lower()
    
    def test_create_user_already_exists(self, client, db):
        """Test POST /api/users - user ID already exists (line 31)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        user_id = f"existing_user_{timestamp}"
        
        # Create existing user
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "name": "Existing User",
            "email": f"{user_id}@example.com",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # Try to create user with same ID
            response = client.post("/api/users", json={
                "user_id": user_id,
                "name": "New User",
                "email": "different@example.com"
            })
            
            assert response.status_code == 409
            assert "already exists" in response.get_json()["error"].lower()
        finally:
            db.collection("users").document(user_id).delete()
    
    def test_create_user_email_already_exists(self, client, db):
        """Test POST /api/users - email already exists (line 34)."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        user_id1 = f"user1_{timestamp}"
        user_id2 = f"user2_{timestamp}"
        email = f"shared_{timestamp}@example.com"
        
        # Create user with email
        db.collection("users").document(user_id1).set({
            "user_id": user_id1,
            "name": "User 1",
            "email": email,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # Try to create another user with same email
            response = client.post("/api/users", json={
                "user_id": user_id2,
                "name": "User 2",
                "email": email
            })
            
            assert response.status_code == 409
            assert "email already exists" in response.get_json()["error"].lower()
        finally:
            db.collection("users").document(user_id1).delete()
    
    def test_get_user_by_email_not_found(self, client, db):
        """Test get_user_by_email helper returns None (line 15)."""
        # This is tested indirectly - when email doesn't exist, get_user_by_email returns None
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        unique_email = f"nonexistent_{timestamp}@example.com"
        user_id = f"newuser_{timestamp}"
        
        # Create user with unique email - should succeed because email doesn't exist
        response = client.post("/api/users", json={
            "user_id": user_id,
            "name": "New User",
            "email": unique_email
        })
        
        try:
            assert response.status_code == 201
            data = response.get_json()
            assert data["user"]["email"] == unique_email
        finally:
            db.collection("users").document(user_id).delete()
    
    def test_get_user_not_found(self, client, db):
        """Test GET /api/users/<user_id> - user not found (line 50)."""
        response = client.get("/api/users/nonexistent_user_12345")
        assert response.status_code == 404
        assert "not found" in response.get_json()["error"].lower()
    
    def test_get_user_role_not_found(self, client, db):
        """Test GET /api/users/<user_id>/role - user not found (line 58)."""
        response = client.get("/api/users/nonexistent_user_67890/role")
        assert response.status_code == 404
        assert "not found" in response.get_json()["error"].lower()
    
    def test_get_user_role_with_default(self, client, db):
        """Test GET /api/users/<user_id>/role - returns default role 'staff'."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        user_id = f"norole_user_{timestamp}"
        
        # Create user without role field
        db.collection("users").document(user_id).set({
            "user_id": user_id,
            "name": "No Role User",
            "email": f"{user_id}@example.com",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            response = client.get(f"/api/users/{user_id}/role")
            assert response.status_code == 200
            data = response.get_json()
            assert data["role"] == "staff"  # Default role
        finally:
            db.collection("users").document(user_id).delete()
    
    def test_create_user_success_full_flow(self, client, db):
        """Test successful user creation covering all branches."""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        user_id = f"complete_user_{timestamp}"
        email = f"complete_{timestamp}@example.com"
        
        try:
            response = client.post("/api/users", json={
                "user_id": user_id,
                "name": "Complete User",
                "email": email
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert "user" in data
            assert data["user"]["user_id"] == user_id
            assert data["user"]["email"] == email.lower()
            assert "created_at" in data["user"]
            
            # Verify user exists
            response = client.get(f"/api/users/{user_id}")
            assert response.status_code == 200
        finally:
            db.collection("users").document(user_id).delete()
