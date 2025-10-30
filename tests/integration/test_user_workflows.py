"""Integration tests for user workflows using real Firebase."""
import pytest
import json
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter


class TestUserManagementIntegration:
    """Test real user management operations with Firebase."""
    
    def test_create_user_in_firestore(self, db, test_collection_prefix, cleanup_collections):
        """Test creating a user directly in Firestore."""
        collection_name = f"{test_collection_prefix}_users"
        cleanup_collections.append(collection_name)
        
        user_id = f"integration_user_{datetime.now(timezone.utc).timestamp()}"
        user_data = {
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "name": "Integration Test User",
            "role": "Member",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Create user in Firestore
        db.collection(collection_name).document(user_id).set(user_data)
        
        # Verify user was created
        doc = db.collection(collection_name).document(user_id).get()
        assert doc.exists
        assert doc.to_dict()["email"] == user_data["email"]
        assert doc.to_dict()["name"] == user_data["name"]
        
        # Cleanup
        db.collection(collection_name).document(user_id).delete()
    
    
    def test_update_user_in_firestore(self, db, test_user):
        """Test updating a user in Firestore."""
        collection = test_user["collection"]
        user_id = test_user["user_id"]
        
        # Update user
        db.collection(collection).document(user_id).update({
            "name": "Updated Name",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify update
        doc = db.collection(collection).document(user_id).get()
        assert doc.exists
        assert doc.to_dict()["name"] == "Updated Name"
        assert "updated_at" in doc.to_dict()
    
    
    def test_delete_user_from_firestore(self, db, test_collection_prefix, cleanup_collections):
        """Test deleting a user from Firestore."""
        collection_name = f"{test_collection_prefix}_users"
        cleanup_collections.append(collection_name)
        
        user_id = f"temp_user_{datetime.now(timezone.utc).timestamp()}"
        
        # Create user
        db.collection(collection_name).document(user_id).set({
            "user_id": user_id,
            "email": f"{user_id}@example.com"
        })
        
        # Verify exists
        assert db.collection(collection_name).document(user_id).get().exists
        
        # Delete user
        db.collection(collection_name).document(user_id).delete()
        
        # Verify deleted
        assert not db.collection(collection_name).document(user_id).get().exists


class TestUserListingIntegration:
    """Test user listing and querying with real Firebase."""
    
    def test_list_users_from_collection(self, db, test_collection_prefix, cleanup_collections):
        """Test retrieving all users from a collection."""
        collection_name = f"{test_collection_prefix}_users"
        cleanup_collections.append(collection_name)
        
        # Create multiple users
        users = []
        for i in range(3):
            user_id = f"list_user_{i}_{datetime.now(timezone.utc).timestamp()}"
            user_data = {
                "user_id": user_id,
                "email": f"{user_id}@example.com",
                "name": f"User {i}",
                "role": "Member"
            }
            db.collection(collection_name).document(user_id).set(user_data)
            users.append(user_id)
        
        # List all users
        docs = db.collection(collection_name).stream()
        retrieved_users = [doc.to_dict() for doc in docs]
        
        assert len(retrieved_users) >= 3
        retrieved_ids = [u["user_id"] for u in retrieved_users]
        for user_id in users:
            assert user_id in retrieved_ids
        
        # Cleanup
        for user_id in users:
            db.collection(collection_name).document(user_id).delete()
    
    
    def test_query_users_by_role(self, db, test_collection_prefix, cleanup_collections):
        """Test querying users by role."""
        collection_name = f"{test_collection_prefix}_users"
        cleanup_collections.append(collection_name)
        
        # Create users with different roles
        admin_id = f"admin_{datetime.now(timezone.utc).timestamp()}"
        member_id = f"member_{datetime.now(timezone.utc).timestamp()}"
        
        db.collection(collection_name).document(admin_id).set({
            "user_id": admin_id,
            "role": "Admin",
            "email": f"{admin_id}@example.com"
        })
        
        db.collection(collection_name).document(member_id).set({
            "user_id": member_id,
            "role": "Member",
            "email": f"{member_id}@example.com"
        })
        
        # Query for admins only
        admin_docs = db.collection(collection_name).where(filter=FieldFilter("role", "==", "Admin")).stream()
        admins = [doc.to_dict() for doc in admin_docs]
        
        # Verify query results
        admin_ids = [a["user_id"] for a in admins]
        assert admin_id in admin_ids
        assert member_id not in admin_ids
        
        # Cleanup
        db.collection(collection_name).document(admin_id).delete()
        db.collection(collection_name).document(member_id).delete()
