"""
Tests for admin department management endpoint to achieve 100% coverage.
Covers lines 623-675 in backend/api/admin.py
"""
import pytest
from unittest.mock import Mock, patch
from conftest import fake_firestore


class TestChangeDepartment:
    """Tests for PUT /admin/users/<user_id>/department"""
    
    def test_change_department_success(self, client, mock_db):
        """Test successfully changing user department"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin", "name": "Admin"}
        
        # Mock user to update
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "name": "Test User",
            "email": "user@test.com",
            "department": "Finance & Accounting"
        }
        
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_user
        mock_user_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        mock_doc_ref = Mock()
                        mock_doc_ref.get.return_value = mock_admin
                        return mock_doc_ref
                    elif doc_id == "user123":
                        return mock_user_ref
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.admin.firestore.client', return_value=mock_db):
            response = client.put(
                '/api/admin/users/user123/department',
                json={"department": "Operations"},
                headers={"X-User-Id": "admin123"}
            )
        
        assert response.status_code == 200
        assert mock_user_ref.update.called
    
    def test_change_department_no_admin_id(self, client, mock_db):
        """Test changing department without admin_id"""
        with patch('backend.api.admin.firestore.client', return_value=mock_db):
            response = client.put(
                '/api/admin/users/user123/department',
                json={"department": "Operations"}
            )
        
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "admin_id required" in data["error"]
    
    def test_change_department_not_admin(self, client, mock_db):
        """Test changing department by non-admin user"""
        # Mock non-admin user
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_user
                mock_coll.document = Mock(return_value=mock_doc_ref)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.admin.firestore.client', return_value=mock_db):
            response = client.put(
                '/api/admin/users/user123/department',
                json={"department": "Operations"},
                headers={"X-User-Id": "staff123"}
            )
        
        assert response.status_code == 403
    
    def test_change_department_missing_field(self, client, mock_db):
        """Test changing department without department field"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_admin
        
        mock_coll = Mock()
        mock_coll.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_coll)
        
        with patch('backend.api.admin.firestore.client', return_value=mock_db):
            response = client.put(
                '/api/admin/users/user123/department',
                json={},
                headers={"X-User-Id": "admin123"}
            )
        
        assert response.status_code == 400
        data = response.get_json()
        assert "department is required" in data["error"]
    
    def test_change_department_invalid_department(self, client, mock_db):
        """Test changing department to invalid value"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_admin
        
        mock_coll = Mock()
        mock_coll.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_coll)
        
        with patch('backend.api.admin.firestore.client', return_value=mock_db):
            response = client.put(
                '/api/admin/users/user123/department',
                json={"department": "Invalid Department"},
                headers={"X-User-Id": "admin123"}
            )
        
        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid department" in data["error"]
    
    def test_change_department_clear_with_empty_string(self, client, mock_db):
        """Test clearing department with empty string"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock user to update
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {
            "name": "Test User",
            "department": ""
        }
        
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_user
        mock_user_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        mock_doc_ref = Mock()
                        mock_doc_ref.get.return_value = mock_admin
                        return mock_doc_ref
                    elif doc_id == "user123":
                        return mock_user_ref
                    return Mock()
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.admin.firestore.client', return_value=mock_db):
            response = client.put(
                '/api/admin/users/user123/department',
                json={"department": ""},
                headers={"X-User-Id": "admin123"}
            )
        
        assert response.status_code == 200
        assert mock_user_ref.update.called
    
    def test_change_department_user_not_found(self, client, mock_db):
        """Test changing department for non-existent user"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock non-existent user
        mock_user = Mock()
        mock_user.exists = False
        
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_user
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        mock_doc_ref = Mock()
                        mock_doc_ref.get.return_value = mock_admin
                        return mock_doc_ref
                    else:
                        return mock_user_ref
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.admin.firestore.client', return_value=mock_db):
            response = client.put(
                '/api/admin/users/user999/department',
                json={"department": "Operations"},
                headers={"X-User-Id": "admin123"}
            )
        
        assert response.status_code == 404
        data = response.get_json()
        assert "User not found" in data["error"]
    
    def test_change_department_update_exception(self, client, mock_db):
        """Test exception during department update"""
        # Mock admin user
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        # Mock user that throws exception on update
        mock_user = Mock()
        mock_user.exists = True
        
        mock_user_ref = Mock()
        mock_user_ref.get.return_value = mock_user
        mock_user_ref.update = Mock(side_effect=Exception("Database error"))
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        mock_doc_ref = Mock()
                        mock_doc_ref.get.return_value = mock_admin
                        return mock_doc_ref
                    else:
                        return mock_user_ref
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.admin.firestore.client', return_value=mock_db):
            response = client.put(
                '/api/admin/users/user123/department',
                json={"department": "Operations"},
                headers={"X-User-Id": "admin123"}
            )
        
        assert response.status_code == 500
        data = response.get_json()
        assert "Failed to update department" in data["error"]
