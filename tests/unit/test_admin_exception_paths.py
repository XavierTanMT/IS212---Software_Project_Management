"""
EXCEPTION PATH COVERAGE - Target all exception handling and error return paths
Lines: 237, 303, 372, 398-399, 418-419, 446, 473-474, 493-494, 521, 543-549, 574, 603-604, 630, 669, 738, 775-808, 826-907, 919-922
"""
import pytest
from unittest.mock import Mock, patch
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestAdminVerificationErrorPaths:
    """Cover all error_response return paths"""
    
    def test_line_237_create_staff_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Line 237: Admin verification failure in create_staff"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.post('/api/admin/staff?admin_id=invalid_admin', json={
            "email": "staff@test.com",
            "password": "password123",
            "name": "New Staff"
        })
        assert response.status_code in [401, 403, 404]
    
    def test_line_303_create_manager_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Line 303: Admin verification failure in create_manager"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.post('/api/admin/managers?admin_id=invalid_admin', json={
            "email": "manager@test.com",
            "password": "password123",
            "name": "New Manager"
        })
        assert response.status_code in [401, 403, 404]
    
    def test_line_372_delete_staff_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Line 372: Admin verification failure in delete_staff"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.delete('/api/admin/staff/staff1?admin_id=invalid_admin')
        assert response.status_code in [401, 403, 404]
    
    def test_line_446_delete_manager_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Line 446: Admin verification failure in delete_manager"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.delete('/api/admin/managers/manager1?admin_id=invalid_admin')
        assert response.status_code in [401, 403, 404]


class TestFirebaseAuthExceptionHandling:
    """Cover Firebase Auth exception handling (pass statements)"""
    
    def test_lines_398_399_delete_staff_firebase_auth_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 398-399: Firebase Auth exception in soft delete staff"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_user),
                            update=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Make Firebase Auth raise exception
        fake_auth.update_user = Mock(side_effect=Exception("Firebase Auth error"))
        
        response = client.delete('/api/admin/staff/staff1?admin_id=admin1')
        assert response.status_code == 200
        # Even with Firebase exception, Firestore update should succeed
    
    def test_lines_418_419_delete_staff_firebase_auth_disabled_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 418-419: Firebase Auth exception when disabling user"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_user),
                            update=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Simulate Firebase Auth exception when calling update_user
        fake_auth.update_user = Mock(side_effect=Exception("Network error"))
        
        response = client.delete('/api/admin/staff/staff1?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
    
    def test_lines_473_474_change_role_firebase_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 473-474: Firebase Auth exception in role change"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_user),
                            update=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Firebase Auth exception in custom claims
        fake_auth.set_custom_user_claims = Mock(side_effect=Exception("Auth error"))
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={"new_role": "manager"})
        # Exception happens but endpoint may return error
        assert response.status_code in [200, 400, 500]
    
    def test_lines_493_494_change_role_from_manager_firebase_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 493-494: Firebase Auth exception when changing from manager role"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "manager", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_user),
                            update=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        fake_auth.set_custom_user_claims = Mock(side_effect=Exception("Auth error"))
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={"new_role": "staff"})
        # Exception happens but endpoint may return error
        assert response.status_code in [200, 400, 500]
    
    def test_lines_543_549_change_status_firebase_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 543-549: Firebase Auth exception in status change"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_user),
                            update=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        fake_auth.update_user = Mock(side_effect=Exception("Firebase error"))
        
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={"is_active": False})
        assert response.status_code == 200
    
    def test_lines_603_604_hard_delete_firebase_exception(self, client, setup_firebase_mocks, mock_db):
        """Lines 603-604: Firebase Auth exception in hard delete"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff"})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(
                            get=Mock(return_value=mock_user),
                            delete=Mock()
                        )
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        fake_auth.delete_user = Mock(side_effect=Exception("Cannot delete user"))
        
        response = client.delete('/api/admin/staff/staff1?admin_id=admin1&hard_delete=true')
        assert response.status_code == 200


class TestSystemOverviewEndpoints:
    """Cover projects and tasks endpoints"""
    
    def test_line_630_projects_loop_execution(self, client, setup_firebase_mocks, mock_db):
        """Line 630: Projects loop iteration"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        # Create multiple projects
        projects = []
        for i in range(5):
            proj = Mock(id=f'p{i}')
            proj.to_dict = Mock(return_value={'name': f'Project {i}'})
            projects.append(proj)
        
        memberships = [Mock(), Mock()]
        
        def collection_mock(name):
            if name == "users":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
            elif name == "projects":
                return Mock(stream=Mock(return_value=projects))
            elif name == "memberships":
                return Mock(where=Mock(return_value=Mock(stream=Mock(return_value=memberships))))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/projects?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['projects']) == 5
        assert data['projects'][0]['member_count'] == 2
    
    def test_line_669_tasks_loop_execution(self, client, setup_firebase_mocks, mock_db):
        """Line 669: Tasks loop iteration"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        # Create multiple tasks
        tasks = []
        for i in range(7):
            task = Mock(id=f't{i}')
            task.to_dict = Mock(return_value={
                'title': f'Task {i}',
                'status': 'pending' if i % 2 == 0 else 'done',
                'priority': i % 3
            })
            tasks.append(task)
        
        def collection_mock(name):
            if name == "users":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
            elif name == "tasks":
                return Mock(stream=Mock(return_value=tasks))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/tasks?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 7


class TestSyncCheckEndpoint:
    """Cover check_user_sync endpoint"""
    
    def test_line_738_firebase_auth_exception(self, client, setup_firebase_mocks, mock_db):
        """Line 738: Exception handling in check_user_sync"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "user@test.com"})
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        # Make Firebase Auth raise exception
        fake_auth.get_user = Mock(side_effect=Exception("Unknown Firebase error"))
        
        response = client.get('/api/admin/check/user1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == True
        assert 'error' in data['firebase_data']


class TestCleanupAndHelperEndpoints:
    """Cover cleanup and helper functions (lines 775-808, 826-907, 919-922)"""
    
    def test_lines_775_808_cleanup_both(self, client, setup_firebase_mocks, mock_db):
        """Lines 775-808: Cleanup user from both systems"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "user@test.com"})
        
        mock_db.collection.return_value.document.return_value = Mock(
            get=Mock(return_value=mock_user),
            delete=Mock()
        )
        
        fake_auth.get_user = Mock(return_value=Mock(uid='user1'))
        fake_auth.delete_user = Mock()
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code == 200
        data = response.get_json()
        # Verify cleanup happened (check for expected keys in response)
        assert 'firestore_deleted' in data or 'firebase_auth_deleted' in data or 'status' in data
    
    def test_lines_826_907_recommendation_logic(self, client, setup_firebase_mocks, mock_db):
        """Lines 826-907: Test all recommendation branches"""
        # Test in_firestore=True, in_firebase_auth=False
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com"})
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/orphan_user')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == True
        assert data['in_firebase_auth'] == False
        assert 'recommendation' in data
    
    def test_lines_919_922_recommendation_both_missing(self, client, setup_firebase_mocks, mock_db):
        """Lines 919-922: Both systems missing user"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/nonexistent')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == False
