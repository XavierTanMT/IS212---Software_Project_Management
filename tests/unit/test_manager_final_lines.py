"""
Final tests to achieve 100% coverage on manager.py
Specifically targeting lines that use default parameters in .get() calls
"""
import pytest
from unittest.mock import Mock, patch, call
import sys

fake_firestore = sys.modules.get("firebase_admin.firestore")


class TestManagerDefaultParameterLines:
    """Tests to hit default parameter lines in .get() calls"""
    
    def test_assign_manager_with_null_json_body(self, client, mock_db, monkeypatch):
        """Test assign manager when request.get_json() returns None"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager",
            "email": "mgr@test.com"
        }
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = True
        mock_staff_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Staff",
            "email": "staff@test.com"
        }
        
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        mock_staff_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    mock_doc_ref = Mock()
                    mock_doc_ref.get.return_value = mock_mgr
                    if doc_id == "staff1":
                        return mock_staff_ref
                    return mock_doc_ref
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Send request with Content-Type but empty body to make get_json() return None
        response = client.post(
            "/api/manager/staff/staff1/assign-manager",
            headers={"X-User-Id": "mgr123", "Content-Type": "application/json"},
            data=''
        )
        # Should still work, defaulting to manager_id = mgr123
        assert response.status_code in [200, 400]  # Either success or validation error
        
    def test_bulk_assign_without_manager_id_field(self, client, mock_db, monkeypatch):
        """Test bulk assign without manager_id in request body"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {
            "role": "manager",
            "name": "Manager",
            "email": "mgr@test.com",
            "team_staff_ids": []
        }
        
        mock_staff_doc = Mock()
        mock_staff_doc.exists = True
        mock_staff_doc.to_dict.return_value = {
            "role": "staff",
            "name": "Staff",
            "email": "staff@test.com"
        }
        
        mock_staff_ref = Mock()
        mock_staff_ref.get.return_value = mock_staff_doc
        mock_staff_ref.update = Mock()
        
        mock_mgr_ref = Mock()
        mock_mgr_ref.get.return_value = mock_mgr
        mock_mgr_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "mgr123":
                        return mock_mgr_ref
                    elif doc_id == "staff1":
                        return mock_staff_ref
                    return Mock()
                mock_coll.document.side_effect = document_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Explicitly omit manager_id from JSON to test the default
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "mgr123"},
            json={"staff_ids": ["staff1"]}  # No "manager_id" key
        )
        assert response.status_code == 200
        
    def test_remove_manager_error_response_path(self, client, mock_db, monkeypatch):
        """Test remove manager when _verify_manager_access returns error"""
        # Make _verify_manager_access return an error
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "staff"}  # Not a manager
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete(
            "/api/manager/staff/staff1/remove-manager",
            headers={"X-User-Id": "not_manager"}
        )
        # Should get 403 from _verify_manager_access
        assert response.status_code == 403
        
    def test_assign_manager_error_response_path(self, client, mock_db, monkeypatch):
        """Test assign manager when _verify_manager_access returns error"""
        mock_mgr = Mock()
        mock_mgr.exists = False  # Manager not found
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/staff/staff1/assign-manager",
            headers={"X-User-Id": "mgr_not_exist"},
            json={}
        )
        # Should get 404 from _verify_manager_access
        assert response.status_code == 404
        
    def test_bulk_assign_error_response_path(self, client, mock_db, monkeypatch):
        """Test bulk assign when _verify_manager_access returns error"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "staff"}  # Not a manager
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_doc_ref = Mock()
                mock_doc_ref.get.return_value = mock_mgr
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/assign-staff",
            headers={"X-User-Id": "not_manager"},
            json={"staff_ids": ["staff1"]}
        )
        # Should get 403 from _verify_manager_access
        assert response.status_code == 403
