"""
Comprehensive tests to achieve 100% coverage for memberships.py
Tests add/remove members, RBAC, and all edge cases
"""
import pytest
from unittest.mock import Mock, MagicMock, patch


class TestAddMember:
    """Tests for POST /api/memberships endpoint"""
    
    def test_add_member_success(self, client, mock_db):
        """Test successfully adding a member"""
        mock_ref = Mock()
        mock_ref.set = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        response = client.post("/api/memberships", json={
            "project_id": "proj123",
            "user_id": "user456",
            "role": "contributor"
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["project_id"] == "proj123"
        assert data["user_id"] == "user456"
        assert data["role"] == "contributor"
        assert "added_at" in data
    
    def test_add_member_default_role(self, client, mock_db):
        """Test adding member with default role"""
        mock_ref = Mock()
        mock_ref.set = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        response = client.post("/api/memberships", json={
            "project_id": "proj123",
            "user_id": "user456"
            # No role specified
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["role"] == "contributor"  # Default role
    
    def test_add_member_missing_project_id(self, client, mock_db):
        """Test adding member without project_id"""
        response = client.post("/api/memberships", json={
            "user_id": "user456"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "project_id and user_id are required" in data["error"]
    
    def test_add_member_missing_user_id(self, client, mock_db):
        """Test adding member without user_id"""
        response = client.post("/api/memberships", json={
            "project_id": "proj123"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "project_id and user_id are required" in data["error"]
    
    def test_add_member_with_viewer_admin(self, client, mock_db):
        """Test adding member as admin user"""
        # Mock admin user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "admin"}
        
        mock_ref = Mock()
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/memberships", 
            headers={"X-User-Id": "admin123"},
            json={
                "project_id": "proj123",
                "user_id": "user456"
            })
        
        assert response.status_code == 201
    
    def test_add_member_with_viewer_manager(self, client, mock_db):
        """Test adding member as manager user"""
        # Mock manager user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "manager"}
        
        mock_ref = Mock()
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/memberships", 
            headers={"X-User-Id": "manager123"},
            json={
                "project_id": "proj123",
                "user_id": "user456"
            })
        
        assert response.status_code == 201
    
    def test_add_member_staff_denied(self, client, mock_db):
        """Test staff user cannot add members"""
        # Mock staff user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "staff"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        response = client.post("/api/memberships", 
            headers={"X-User-Id": "staff123"},
            json={
                "project_id": "proj123",
                "user_id": "user456"
            })
        
        assert response.status_code == 403
        data = response.get_json()
        assert "Permission denied" in data["error"]
    
    def test_add_member_viewer_not_found(self, client, mock_db):
        """Test adding member when viewer doesn't exist"""
        # Mock user not found
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        
        mock_ref = Mock()
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/memberships", 
            headers={"X-User-Id": "nonexistent"},
            json={
                "project_id": "proj123",
                "user_id": "user456"
            })
        
        # Should treat as staff and deny
        assert response.status_code == 403
    
    def test_add_member_viewer_exception(self, client, mock_db):
        """Test adding member when fetching viewer raises exception"""
        # Mock exception when getting user
        mock_ref = Mock()
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.side_effect = Exception("DB error")
            elif name == "memberships":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/memberships", 
            headers={"X-User-Id": "user123"},
            json={
                "project_id": "proj123",
                "user_id": "user456"
            })
        
        # Should treat as staff and deny
        assert response.status_code == 403
    
    def test_add_member_no_viewer(self, client, mock_db):
        """Test adding member without viewer (automation/test mode)"""
        mock_ref = Mock()
        mock_ref.set = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        # No X-User-Id header, no viewer_id param
        response = client.post("/api/memberships", json={
            "project_id": "proj123",
            "user_id": "user456"
        })
        
        # Should allow when no viewer provided (automation mode)
        assert response.status_code == 201
    
    def test_add_member_viewer_via_query_param(self, client, mock_db):
        """Test adding member with viewer_id as query param"""
        # Mock admin user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "admin"}
        
        mock_ref = Mock()
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/memberships?viewer_id=admin123", json={
            "project_id": "proj123",
            "user_id": "user456"
        })
        
        assert response.status_code == 201


class TestListProjectMembers:
    """Tests for GET /api/memberships/by-project/<project_id> endpoint"""
    
    def test_list_project_members_success(self, client, mock_db):
        """Test listing project members"""
        # Mock memberships
        member1 = Mock()
        member1.to_dict.return_value = {"project_id": "proj123", "user_id": "user1", "role": "contributor"}
        
        member2 = Mock()
        member2.to_dict.return_value = {"project_id": "proj123", "user_id": "user2", "role": "owner"}
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.stream.return_value = [member1, member2]
        
        mock_db.collection.return_value = mock_query
        
        response = client.get("/api/memberships/by-project/proj123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]["user_id"] == "user1"
        assert data[1]["user_id"] == "user2"
    
    def test_list_project_members_empty(self, client, mock_db):
        """Test listing members for project with no members"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.stream.return_value = []
        
        mock_db.collection.return_value = mock_query
        
        response = client.get("/api/memberships/by-project/empty_proj")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 0


class TestRemoveMember:
    """Tests for DELETE /api/memberships/<project_id>/<user_id> endpoint"""
    
    def test_remove_member_success(self, client, mock_db):
        """Test successfully removing a member"""
        # Mock admin user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "admin"}
        
        # Mock membership exists
        mock_membership = Mock()
        mock_membership.exists = True
        mock_membership_ref = Mock()
        mock_membership_ref.get.return_value = mock_membership
        mock_membership_ref.delete = Mock()
        
        # Mock project (user is not owner)
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {"owner_id": "different_user"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_membership_ref
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_project
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/memberships/proj123/user456",
            headers={"X-User-Id": "admin123"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert data["project_id"] == "proj123"
        assert data["user_id"] == "user456"
        mock_membership_ref.delete.assert_called_once()
    
    def test_remove_member_no_viewer(self, client, mock_db):
        """Test removing member without viewer_id"""
        response = client.delete("/api/memberships/proj123/user456")
        
        assert response.status_code == 401
        data = response.get_json()
        assert "viewer_id required" in data["error"]
    
    def test_remove_member_staff_denied(self, client, mock_db):
        """Test staff user cannot remove members"""
        # Mock staff user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "staff"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        response = client.delete("/api/memberships/proj123/user456",
            headers={"X-User-Id": "staff123"})
        
        assert response.status_code == 403
        data = response.get_json()
        assert "Permission denied" in data["error"]
    
    def test_remove_member_not_found(self, client, mock_db):
        """Test removing non-existent membership"""
        # Mock admin user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "admin"}
        
        # Mock membership doesn't exist
        mock_membership = Mock()
        mock_membership.exists = False
        mock_membership_ref = Mock()
        mock_membership_ref.get.return_value = mock_membership
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_membership_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/memberships/proj123/user456",
            headers={"X-User-Id": "admin123"})
        
        assert response.status_code == 404
        data = response.get_json()
        assert "Membership not found" in data["error"]
    
    def test_remove_member_project_owner(self, client, mock_db):
        """Test cannot remove project owner"""
        # Mock admin user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "admin"}
        
        # Mock membership exists
        mock_membership = Mock()
        mock_membership.exists = True
        mock_membership_ref = Mock()
        mock_membership_ref.get.return_value = mock_membership
        
        # Mock project (user IS owner)
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {"owner_id": "user456"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_membership_ref
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_project
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/memberships/proj123/user456",
            headers={"X-User-Id": "admin123"})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Cannot remove the project owner" in data["error"]
    
    def test_remove_member_project_not_found(self, client, mock_db):
        """Test removing member when project doesn't exist"""
        # Mock admin user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "admin"}
        
        # Mock membership exists
        mock_membership = Mock()
        mock_membership.exists = True
        mock_membership_ref = Mock()
        mock_membership_ref.get.return_value = mock_membership
        mock_membership_ref.delete = Mock()
        
        # Mock project doesn't exist
        mock_project = Mock()
        mock_project.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_membership_ref
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_project
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/memberships/proj123/user456",
            headers={"X-User-Id": "admin123"})
        
        # Should succeed - project not existing doesn't prevent removal
        assert response.status_code == 200
        mock_membership_ref.delete.assert_called_once()
    
    def test_remove_member_project_todict_exception(self, client, mock_db):
        """Test removing member when project to_dict raises exception"""
        # Mock admin user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "admin"}
        
        # Mock membership exists
        mock_membership = Mock()
        mock_membership.exists = True
        mock_membership_ref = Mock()
        mock_membership_ref.get.return_value = mock_membership
        mock_membership_ref.delete = Mock()
        
        # Mock project that exists but to_dict raises exception
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.side_effect = Exception("Serialization error")
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_membership_ref
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_project
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        # Should handle exception in try block and proceed with deletion
        response = client.delete("/api/memberships/proj123/user456",
            headers={"X-User-Id": "admin123"})
        
        # Should succeed - exception is caught in try/except block
        assert response.status_code == 200
        mock_membership_ref.delete.assert_called_once()
    
    def test_remove_member_viewer_via_query_param(self, client, mock_db):
        """Test removing member with viewer_id as query param"""
        # Mock manager user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"role": "manager"}
        
        # Mock membership exists
        mock_membership = Mock()
        mock_membership.exists = True
        mock_membership_ref = Mock()
        mock_membership_ref.get.return_value = mock_membership
        mock_membership_ref.delete = Mock()
        
        # Mock project
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {"owner_id": "other_user"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "memberships":
                mock_coll.document.return_value = mock_membership_ref
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_project
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/memberships/proj123/user456?viewer_id=manager123")
        
        assert response.status_code == 200
    
    def test_remove_member_viewer_not_found(self, client, mock_db):
        """Test removing member when viewer doesn't exist"""
        # Mock user not found
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        response = client.delete("/api/memberships/proj123/user456",
            headers={"X-User-Id": "nonexistent"})
        
        # Should treat as staff and deny
        assert response.status_code == 403
    
    def test_remove_member_viewer_exception(self, client, mock_db):
        """Test removing member when fetching viewer raises exception"""
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.side_effect = Exception("DB error")
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/memberships/proj123/user456",
            headers={"X-User-Id": "user123"})
        
        # Should treat as staff and deny
        assert response.status_code == 403
