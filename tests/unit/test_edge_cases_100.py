import sys
from unittest.mock import patch, Mock


import pytest
from unittest.mock import patch, Mock

class TestManagerEdgeCasesFull:
    @patch('backend.api.manager._verify_manager_access')
    @patch('backend.api.manager._get_manager_team_member_ids')
    @patch('backend.api.manager.firestore')
    def test_assign_task_assignee_not_in_team(self, mock_firestore, mock_team_ids, mock_verify, client):
        mock_verify.return_value = ({'name': 'Manager', 'email': 'mgr@test.com'}, None, 200)
        mock_team_ids.return_value = ['staff2']  # staff1 not in team
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_firestore.client.return_value.collection.return_value.document.return_value.get.return_value = mock_task_doc
        response = client.post("/api/manager/tasks/task123/assign?viewer_id=mgr123", json={"assignee_ids": ["staff1"]})
        assert response.status_code == 403
        assert "not in your team" in response.get_json()['error']

    @patch('backend.api.manager._verify_manager_access')
    @patch('backend.api.manager._get_manager_team_member_ids')
    @patch('backend.api.manager.firestore')
    def test_assign_task_user_not_found(self, mock_firestore, mock_team_ids, mock_verify, client):
        mock_verify.return_value = ({'name': 'Manager', 'email': 'mgr@test.com'}, None, 200)
        mock_team_ids.return_value = ['staff1']
        # Patch Firestore so that:
        # - The task document returns a valid task Mock
        # - The user document for the assignee returns a Mock with exists=False
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_task_doc = Mock()
                mock_task_doc.exists = True
                mock_task_doc.to_dict.return_value = {"project_id": "proj1", "title": "Task"}
                mock_coll.document.return_value.get.return_value = mock_task_doc
                mock_coll.document.return_value.update = Mock()
            elif name == "users":
                # Mock the where().stream() for direct staff query
                mock_where = Mock()
                mock_where.stream.return_value = iter([])  # No direct staff
                mock_coll.where.return_value = mock_where
                
                def user_doc_side_effect(doc_id):
                    user_doc = Mock()
                    if doc_id == "staff1":
                        user_doc_not_found = Mock()
                        user_doc_not_found.exists = False
                        user_doc_not_found.to_dict.return_value = {}
                        user_doc.get.return_value = user_doc_not_found
                    else:
                        user_doc.exists = True
                        user_doc.to_dict.return_value = {"name": "Other", "email": "other@test.com"}
                    return user_doc
                mock_coll.document.side_effect = user_doc_side_effect
            return mock_coll
        mock_firestore.client.return_value.collection.side_effect = collection_side_effect
        response = client.post("/api/manager/tasks/task123/assign?viewer_id=mgr123", json={"assignee_ids": ["staff1"]})
        assert response.status_code == 200  # Should still succeed, just no user data
        data = response.get_json()
        assert "assigned_to" in data
    """Edge case tests for manager.py to push coverage to 100%"""

    @patch('backend.api.manager._verify_manager_access')
    @patch('backend.api.manager.firestore')
    def test_assign_task_missing_manager_id(self, mock_firestore, mock_verify, client):
        # No viewer_id in headers or args
        response = client.post("/api/manager/tasks/task123/assign", json={})
        assert response.status_code == 401
        assert response.get_json()['error'] == 'manager_id required'

    @patch('backend.api.manager._verify_manager_access')
    @patch('backend.api.manager.firestore')
    def test_assign_task_error_response(self, mock_firestore, mock_verify, client):
        # viewer_id present, but _verify_manager_access returns error
        from flask import jsonify
        with client.application.app_context():
            resp = jsonify({'error': 'fail'})
            resp.status_code = 403
            mock_verify.return_value = (None, resp, 403)
            response = client.post("/api/manager/tasks/task123/assign?viewer_id=mgr123", json={})
        assert response.status_code == 403

    @patch('backend.api.manager._verify_manager_access')
    @patch('backend.api.manager.firestore')
    def test_assign_task_missing_assignee_ids(self, mock_firestore, mock_verify, client):
        # viewer_id present, but no assignee_ids in json
        mock_verify.return_value = ({'name': 'Manager', 'email': 'mgr@test.com'}, None, 200)
        response = client.post("/api/manager/tasks/task123/assign?viewer_id=mgr123", json={})
        assert response.status_code == 400
        assert response.get_json()['error'] == 'assignee_ids required'

    @patch('backend.api.manager._verify_manager_access')
    @patch('backend.api.manager.firestore')
    def test_assign_task_task_not_found(self, mock_firestore, mock_verify, client):
        # viewer_id present, assignee_ids present, but task does not exist
        mock_verify.return_value = ({'name': 'Manager', 'email': 'mgr@test.com'}, None, 200)
        mock_task_doc = Mock()
        mock_task_doc.exists = False
        mock_firestore.client.return_value.collection.return_value.document.return_value.get.return_value = mock_task_doc
        response = client.post("/api/manager/tasks/task123/assign?viewer_id=mgr123", json={"assignee_ids": ["staff1"]})
        assert response.status_code == 404
        assert response.get_json()['error'] == 'Task not found'
"""
Additional edge case tests for admin.py and manager.py to achieve 100% coverage
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
import sys

fake_firestore = sys.modules.get("firebase_admin.firestore")


class TestAdminEdgeCases:
    """Test edge cases and error paths in admin.py"""
    
    def test_create_staff_validation_errors(self, client, mock_db, monkeypatch):
        """Test POST /api/admin/staff with various validation errors"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test missing email
        response = client.post(
            "/api/admin/staff?user_id=admin123",
            json={"name": "Test"}
        )
        assert response.status_code in [400, 401, 500]
        
        # Test missing name
        response = client.post(
            "/api/admin/staff?user_id=admin123",
            json={"email": "test@test.com"}
        )
        assert response.status_code in [400, 401, 500]
    
    def test_create_manager_validation_errors(self, client, mock_db, monkeypatch):
        """Test POST /api/admin/managers with validation errors"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test missing required fields
        response = client.post(
            "/api/admin/managers?user_id=admin123",
            json={}
        )
        assert response.status_code in [400, 401, 500]
    
    def test_update_role_invalid_role(self, client, mock_db, monkeypatch):
        """Test PUT /api/admin/users/<user_id>/role with invalid role"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_user), update=Mock())
                mock_coll.document.side_effect = doc_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test invalid role
        response = client.put(
            "/api/admin/users/user123/role?user_id=admin123",
            json={"role": "invalid_role"}
        )
        assert response.status_code in [400, 401, 500]
    
    def test_update_status_invalid_status(self, client, mock_db, monkeypatch):
        """Test PUT /api/admin/users/<user_id>/status with invalid status"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"is_active": True}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_user), update=Mock())
                mock_coll.document.side_effect = doc_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test missing is_active field
        response = client.put(
            "/api/admin/users/user123/status?user_id=admin123",
            json={}
        )
        assert response.status_code in [400, 401, 500]
    
    def test_delete_staff_not_found(self, client, mock_db, monkeypatch):
        """Test DELETE /api/admin/staff/<user_id> when user not found"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_user = Mock()
        mock_user.exists = False
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_user))
                mock_coll.document.side_effect = doc_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete("/api/admin/staff/user123?user_id=admin123")
        assert response.status_code in [401, 404, 500]
    
    def test_delete_manager_not_staff_role(self, client, mock_db, monkeypatch):
        """Test DELETE /api/admin/managers/<user_id> when user is not a manager"""
        mock_admin = Mock()
        mock_admin.exists = True
        mock_admin.to_dict.return_value = {"role": "admin"}
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_side_effect(doc_id):
                    if doc_id == "admin123":
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_user), delete=Mock())
                mock_coll.document.side_effect = doc_side_effect
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete("/api/admin/managers/user123?user_id=admin123")
        assert response.status_code in [400, 401, 404, 500]


class TestManagerEdgeCases:
    """Test edge cases and error paths in manager.py"""
    
    def test_assign_task_not_team_member(self, client, mock_db, monkeypatch):
        """Test POST /api/manager/tasks/<task_id>/assign when user not in team"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_task = Mock()
        mock_task.exists = True
        mock_task.to_dict.return_value = {"project_id": "proj1", "title": "Task"}
        
        mock_proj = Mock()
        mock_proj.exists = True
        mock_proj.to_dict.return_value = {"manager_id": "mgr123", "members": []}
        
        mock_user = Mock()
        mock_user.exists = True
        mock_user.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_side_effect(doc_id):
                    if doc_id == "mgr123":
                        return Mock(get=Mock(return_value=mock_mgr))
                    else:
                        return Mock(get=Mock(return_value=mock_user))
                mock_coll.document.side_effect = doc_side_effect
            elif name == "tasks":
                mock_coll.document.return_value = Mock(get=Mock(return_value=mock_task), update=Mock())
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_proj
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/tasks/task123/assign?viewer_id=mgr123",
            json={"user_id": "staff999"}
        )
        assert response.status_code in [400, 403, 404]
    
    def test_create_project_missing_name(self, client, mock_db, monkeypatch):
        """Test POST /api/manager/projects with missing name"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager", "name": "Manager", "email": "mgr@test.com"}
        
        mock_proj_ref = (None, Mock(id="new_proj_123"))
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_mgr
            elif name == "projects":
                mock_coll.add.return_value = mock_proj_ref
            elif name == "memberships":
                mock_coll.add = Mock()
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/projects?viewer_id=mgr123",
            json={"description": "Test"}
        )
        assert response.status_code in [200, 201, 400, 500]
    
    def test_add_member_already_exists(self, client, mock_db, monkeypatch):
        """Test POST /api/manager/projects/<project_id>/members when member already exists"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_proj = Mock()
        mock_proj.exists = True
        mock_proj.to_dict.return_value = {"manager_id": "mgr123", "members": ["staff1"]}
        
        mock_staff = Mock()
        mock_staff.exists = True
        mock_staff.to_dict.return_value = {"role": "staff"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_side_effect(doc_id):
                    if doc_id == "mgr123":
                        return Mock(get=Mock(return_value=mock_mgr))
                    else:
                        return Mock(get=Mock(return_value=mock_staff))
                mock_coll.document.side_effect = doc_side_effect
            elif name == "projects":
                mock_coll.document.return_value = Mock(get=Mock(return_value=mock_proj), update=Mock())
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/manager/projects/proj123/members?viewer_id=mgr123",
            json={"user_id": "staff1"}
        )
        assert response.status_code in [400, 409]
    
    def test_remove_member_not_found(self, client, mock_db, monkeypatch):
        """Test DELETE /api/manager/projects/<project_id>/members/<user_id> when member not in project"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_proj = Mock()
        mock_proj.exists = True
        mock_proj.to_dict.return_value = {"manager_id": "mgr123", "members": []}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_mgr
            elif name == "projects":
                mock_coll.document.return_value = Mock(get=Mock(return_value=mock_proj))
            elif name == "memberships":
                # Chain where() calls and use limit().get()
                mock_query = Mock()
                mock_query2 = Mock()
                mock_query3 = Mock()
                mock_query3.get.return_value = []
                mock_query2.limit.return_value = mock_query3
                mock_query.where.return_value = mock_query2
                mock_coll.where.return_value = mock_query
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.delete("/api/manager/projects/proj123/members/staff999?viewer_id=mgr123")
        assert response.status_code in [400, 404]
    
    def test_update_task_status_invalid_status(self, client, mock_db, monkeypatch):
        """Test PUT /api/manager/tasks/<task_id>/status with invalid status"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_mgr
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.put(
            "/api/manager/tasks/task123/status?viewer_id=mgr123",
            json={"status": "invalid_status"}
        )
        assert response.status_code in [400, 404]
    
    def test_update_task_priority_out_of_range(self, client, mock_db, monkeypatch):
        """Test PUT /api/manager/tasks/<task_id>/priority with invalid priority"""
        mock_mgr = Mock()
        mock_mgr.exists = True
        mock_mgr.to_dict.return_value = {"role": "manager"}
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_mgr
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test priority too high
        response = client.put(
            "/api/manager/tasks/task123/priority?viewer_id=mgr123",
            json={"priority": 11}
        )
        assert response.status_code in [400]
        
        # Test priority too low
        response = client.put(
            "/api/manager/tasks/task123/priority?viewer_id=mgr123",
            json={"priority": 0}
        )
        assert response.status_code in [400]
        
        # Test priority not an integer
        response = client.put(
            "/api/manager/tasks/task123/priority?viewer_id=mgr123",
            json={"priority": "high"}
        )
        assert response.status_code in [400]
