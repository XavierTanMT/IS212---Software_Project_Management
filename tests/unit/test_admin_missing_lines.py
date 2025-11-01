"""
Targeted tests to achieve 100% coverage for backend/api/admin.py
Focuses on missing lines identified in coverage report
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import sys

fake_firestore = sys.modules.get("firebase_admin.firestore")
fake_auth = sys.modules.get("firebase_admin.auth")


class TestAdminMissingLines:
    """Tests targeting specific missing lines in admin.py"""
    
    # Lines 139-149: GET /api/admin/statistics
    def test_statistics_endpoint(self, client, mock_db, monkeypatch):
        """Cover lines 139-149 - statistics endpoint"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                mock_coll.stream = Mock(return_value=[Mock(), Mock()])
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=[Mock()])
            elif name == "projects":
                mock_coll.stream = Mock(return_value=[Mock()])
            elif name == "memberships":
                mock_coll.stream = Mock(return_value=[Mock()])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        response = client.get("/api/admin/statistics?admin_id=admin123")
        assert response.status_code == 200
    
    # Lines 177, 182: GET /api/admin/users with role filter
    def test_users_with_role_filter(self, client, mock_db, monkeypatch):
        """Cover lines 177, 182 - role filtering"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_staff = Mock()
        mock_staff.to_dict.return_value = {"role": "staff", "name": "Staff"}
        mock_staff.id = "staff1"
        
        mock_manager = Mock()
        mock_manager.to_dict.return_value = {"role": "manager", "name": "Manager"}
        mock_manager.id = "mgr1"
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                mock_coll.stream = Mock(return_value=[mock_staff, mock_manager])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        response = client.get("/api/admin/users?admin_id=admin123&role=staff")
        assert response.status_code == 200
    
    # Lines 197, 202, 204: GET /api/admin/users with status filter
    def test_users_with_status_filter(self, client, mock_db, monkeypatch):
        """Cover lines 197, 202, 204 - status filtering"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_active = Mock()
        mock_active.to_dict.return_value = {"role": "staff", "is_active": True}
        mock_active.id = "user1"
        
        mock_inactive = Mock()
        mock_inactive.to_dict.return_value = {"role": "staff", "is_active": False}
        mock_inactive.id = "user2"
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                mock_coll.stream = Mock(return_value=[mock_active, mock_inactive])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        # Test active filter
        response = client.get("/api/admin/users?admin_id=admin123&status=active")
        assert response.status_code == 200
        
        # Test inactive filter
        response = client.get("/api/admin/users?admin_id=admin123&status=inactive")
        assert response.status_code == 200
    
    # Line 237: POST /api/admin/staff missing fields
    def test_add_staff_missing_fields(self, client, mock_db, monkeypatch):
        """Cover line 237 - missing required fields"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection = Mock(return_value=Mock(
            document=Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
        ))
        
        response = client.post("/api/admin/staff?admin_id=admin123", json={"email": "test@test.com"})
        assert response.status_code == 400
    
    # Line 247: POST /api/admin/staff Firebase error
    def test_add_staff_firebase_error(self, client, mock_db, monkeypatch):
        """Cover line 247 - Firebase create error"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection = Mock(return_value=Mock(
            document=Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
        ))
        
        fake_auth.create_user = Mock(side_effect=Exception("Firebase error"))
        
        response = client.post("/api/admin/staff?admin_id=admin123", json={
            "email": "test@test.com",
            "password": "pass123",
            "name": "Test User"
        })
        assert response.status_code == 500
    
    # Lines 277-280: POST /api/admin/managers missing fields
    def test_add_manager_missing_fields(self, client, mock_db, monkeypatch):
        """Cover lines 277-280 - missing required fields for manager"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection = Mock(return_value=Mock(
            document=Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
        ))
        
        response = client.post("/api/admin/managers?admin_id=admin123", json={"email": "test@test.com"})
        assert response.status_code == 400
    
    # Line 303: POST /api/admin/managers invalid manager_type
    def test_add_manager_invalid_type(self, client, mock_db, monkeypatch):
        """Cover line 303 - invalid manager type"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection = Mock(return_value=Mock(
            document=Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
        ))
        
        response = client.post("/api/admin/managers?admin_id=admin123", json={
            "email": "test@test.com",
            "password": "pass123",
            "name": "Test Manager",
            "manager_type": "invalid_type"
        })
        assert response.status_code == 400
    
    # Line 314: POST /api/admin/managers Firebase error
    def test_add_manager_firebase_error(self, client, mock_db, monkeypatch):
        """Cover line 314 - Firebase create error for manager"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection = Mock(return_value=Mock(
            document=Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
        ))
        
        fake_auth.create_user = Mock(side_effect=Exception("Firebase error"))
        
        response = client.post("/api/admin/managers?admin_id=admin123", json={
            "email": "test@test.com",
            "password": "pass123",
            "name": "Test Manager"
        })
        assert response.status_code == 500
    
    # Lines 349-352, 372: DELETE /api/admin/staff/<user_id>
    def test_remove_staff_wrong_role(self, client, mock_db, monkeypatch):
        """Cover lines 349-352, 372 - removing non-staff user"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "manager"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/admin/staff/mgr456?admin_id=admin123")
        assert response.status_code == 400
    
    # Line 381: DELETE /api/admin/staff/<user_id> user not found
    def test_remove_staff_not_found(self, client, mock_db, monkeypatch):
        """Cover line 381 - staff not found"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/admin/staff/nonexistent?admin_id=admin123")
        assert response.status_code == 404
    
    # Line 387: DELETE /api/admin/staff/<user_id> with hard_delete
    def test_remove_staff_hard_delete(self, client, mock_db, monkeypatch):
        """Cover line 387 - hard delete staff"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "staff"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_target)
        mock_doc_ref.delete = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.delete_user = Mock()
        
        response = client.delete("/api/admin/staff/staff456?admin_id=admin123&hard_delete=true")
        assert response.status_code == 200
    
    # Lines 395-401: DELETE /api/admin/staff/<user_id> soft delete
    def test_remove_staff_soft_delete(self, client, mock_db, monkeypatch):
        """Cover lines 395-401 - soft delete staff"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "staff"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_target)
        mock_doc_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.update_user = Mock()
        
        response = client.delete("/api/admin/staff/staff456?admin_id=admin123")
        assert response.status_code == 200
    
    # Lines 418-419: DELETE /api/admin/managers/<user_id> wrong role
    def test_remove_manager_wrong_role(self, client, mock_db, monkeypatch):
        """Cover lines 418-419 - removing non-manager"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/admin/managers/staff456?admin_id=admin123")
        assert response.status_code == 400
    
    # Line 446: DELETE /api/admin/managers/<user_id> not found
    def test_remove_manager_not_found(self, client, mock_db, monkeypatch):
        """Cover line 446 - manager not found"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.delete("/api/admin/managers/nonexistent?admin_id=admin123")
        assert response.status_code == 404
    
    # Line 455: DELETE /api/admin/managers/<user_id> hard delete
    def test_remove_manager_hard_delete(self, client, mock_db, monkeypatch):
        """Cover line 455 - hard delete manager"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "manager"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_target)
        mock_doc_ref.delete = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.delete_user = Mock()
        
        response = client.delete("/api/admin/managers/mgr456?admin_id=admin123&hard_delete=true")
        assert response.status_code == 200
    
    # Lines 462, 470-476: DELETE /api/admin/managers/<user_id> soft delete
    def test_remove_manager_soft_delete(self, client, mock_db, monkeypatch):
        """Cover lines 462, 470-476 - soft delete manager"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "manager"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_target)
        mock_doc_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.update_user = Mock()
        
        response = client.delete("/api/admin/managers/mgr456?admin_id=admin123")
        assert response.status_code == 200
    
    # Lines 493-494, 516, 521: PUT /api/admin/users/<user_id>/role
    def test_change_user_role_invalid(self, client, mock_db, monkeypatch):
        """Cover lines 493-494, 516, 521 - invalid role change"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection = Mock(return_value=Mock(
            document=Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
        ))
        
        # Test invalid role
        response = client.put("/api/admin/users/user456/role?admin_id=admin123", json={
            "role": "invalid_role"
        })
        assert response.status_code == 400
    
    def test_change_user_role_not_found(self, client, mock_db, monkeypatch):
        """Cover line 516 - user not found"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.put("/api/admin/users/nonexistent/role?admin_id=admin123", json={
            "role": "staff"
        })
        assert response.status_code == 404
    
    def test_change_own_role(self, client, mock_db, monkeypatch):
        """Cover line 521 - cannot change own role"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection = Mock(return_value=Mock(
            document=Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
        ))
        
        response = client.put("/api/admin/users/admin123/role?admin_id=admin123", json={
            "role": "staff"
        })
        assert response.status_code == 400
    
    # Lines 532-549, 569, 574: PUT /api/admin/users/<user_id>/status
    def test_change_user_status_not_found(self, client, mock_db, monkeypatch):
        """Cover lines 532-549, 569, 574 - status change user not found"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.put("/api/admin/users/nonexistent/status?admin_id=admin123", json={
            "is_active": True
        })
        assert response.status_code == 404
    
    def test_change_user_status_activate(self, client, mock_db, monkeypatch):
        """Cover lines for activating user"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "staff", "is_active": False}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_target)
        mock_doc_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.update_user = Mock()
        
        response = client.put("/api/admin/users/user456/status?admin_id=admin123", json={
            "is_active": True
        })
        assert response.status_code == 200
    
    def test_change_user_status_deactivate(self, client, mock_db, monkeypatch):
        """Cover lines for deactivating user"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"role": "staff", "is_active": True}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get = Mock(return_value=mock_target)
        mock_doc_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        fake_auth.update_user = Mock()
        
        response = client.put("/api/admin/users/user456/status?admin_id=admin123", json={
            "is_active": False
        })
        assert response.status_code == 200
    
    # Lines 583-606, 625, 630: GET /api/admin/projects and tasks
    def test_get_admin_projects(self, client, mock_db, monkeypatch):
        """Cover lines 583-606 - get projects"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_project = Mock()
        mock_project.to_dict.return_value = {"name": "Project 1"}
        mock_project.id = "proj1"
        
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"user_id": "user1", "project_id": "proj1"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "projects":
                mock_coll.stream = Mock(return_value=[mock_project])
            elif name == "memberships":
                mock_coll.where = Mock(return_value=Mock(stream=Mock(return_value=[mock_membership])))
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/admin/projects?admin_id=admin123")
        assert response.status_code == 200
    
    def test_get_admin_tasks(self, client, mock_db, monkeypatch):
        """Cover lines for getting tasks"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_task = Mock()
        mock_task.to_dict.return_value = {"title": "Task 1"}
        mock_task.id = "task1"
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=[mock_task])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/admin/tasks?admin_id=admin123")
        assert response.status_code == 200
    
    # Lines 664, 669, 684, 686: GET /api/admin/check/<user_id>
    def test_check_user_consistency(self, client, mock_db, monkeypatch):
        """Cover lines 664, 669, 684, 686 - check user consistency"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_target = Mock()
        mock_target.exists = True
        mock_target.to_dict.return_value = {"name": "User", "email": "user@test.com"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def document_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                mock_coll.document = Mock(side_effect=document_side_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        # Mock Firebase Auth user
        mock_auth_user = Mock()
        mock_auth_user.uid = "user456"
        mock_auth_user.email = "user@test.com"
        mock_auth_user.display_name = "User"
        mock_auth_user.disabled = False
        mock_auth_user.email_verified = True
        mock_auth_user.custom_claims = {}
        fake_auth.get_user = Mock(return_value=mock_auth_user)
        
        response = client.get("/api/admin/check/user456?admin_id=admin123")
        assert response.status_code == 200
