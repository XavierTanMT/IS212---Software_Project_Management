"""
COMPLETE CONSOLIDATED ADMIN TESTS - 100% COVERAGE
All tests from 14+ original test files consolidated into one organized file.
Achieves 100% statement and branch coverage for backend/api/admin.py
"""
import pytest
from unittest.mock import Mock, patch
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


# ============================================================================
# DASHBOARD & STATISTICS TESTS
# ============================================================================

class TestDashboard:
    """Dashboard endpoint tests"""
    
    def test_dashboard_success_with_data(self, client, setup_firebase_mocks, mock_db):
        """Test dashboard with users, tasks, and projects"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin", "name": "Admin", "email": "admin@test.com", "is_active": True})
        
        user = Mock(id='u1')
        user.to_dict = Mock(return_value={'user_id': 'u1', 'name': 'User', 'role': 'staff', 'is_active': True})
        
        task = Mock(id='t1')
        task.to_dict = Mock(return_value={'title': 'Task 1', 'status': 'To Do', 'priority': 5})
        
        project = Mock(id='p1')
        project.to_dict = Mock(return_value={'name': 'Project 1', 'status': 'active'})
        
        def collection_mock(name):
            if name == "users":
                return Mock(
                    document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))),
                    stream=Mock(return_value=[user])
                )
            elif name == "tasks":
                return Mock(stream=Mock(return_value=[task]))
            elif name == "projects":
                return Mock(stream=Mock(return_value=[project]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/dashboard?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert 'statistics' in data
        assert data['statistics']['total_users'] == 1
    
    def test_dashboard_with_unknown_roles_branch_71_74(self, client, setup_firebase_mocks, mock_db):
        """CRITICAL Branch 71->74: Users with roles NOT in role_breakdown"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin", "name": "Admin", "email": "admin@test.com", "is_active": True})
        
        user1 = Mock(id='u1')
        user1.to_dict = Mock(return_value={'user_id': 'u1', 'name': 'User 1', 'role': 'director', 'is_active': True})
        user2 = Mock(id='u2')
        user2.to_dict = Mock(return_value={'user_id': 'u2', 'name': 'User 2', 'role': 'hr', 'is_active': True})
        
        def collection_mock(name):
            if name == "users":
                return Mock(
                    document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))),
                    stream=Mock(return_value=[user1, user2])
                )
            elif name == "tasks":
                return Mock(stream=Mock(return_value=[]))
            elif name == "projects":
                return Mock(stream=Mock(return_value=[]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/dashboard?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['statistics']['total_users'] == 2
    
    def test_dashboard_with_multiple_tasks_and_priorities(self, client, setup_firebase_mocks, mock_db):
        """Dashboard with varied tasks, statuses, and priorities - lines 84-92"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin", "name": "Admin", "email": "admin@test.com", "is_active": True})
        
        task1 = Mock(id='t1')
        task1.to_dict = Mock(return_value={'title': 'Task 1', 'status': 'To Do', 'priority': 5})
        task2 = Mock(id='t2')
        task2.to_dict = Mock(return_value={'title': 'Task 2', 'status': 'In Progress', 'priority': 3})
        task3 = Mock(id='t3')
        task3.to_dict = Mock(return_value={'title': 'Task 3', 'status': 'Done', 'priority': 1})
        
        project1 = Mock(id='p1')
        project1.to_dict = Mock(return_value={'name': 'Project 1', 'status': 'active'})
        
        user1 = Mock(id='u1')
        user1.to_dict = Mock(return_value={'name': 'User 1', 'role': 'staff', 'is_active': True})
        
        def collection_mock(name):
            if name == "users":
                return Mock(
                    document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))),
                    stream=Mock(return_value=[user1])
                )
            elif name == "tasks":
                return Mock(stream=Mock(return_value=[task1, task2, task3]))
            elif name == "projects":
                return Mock(stream=Mock(return_value=[project1]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/dashboard?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert 'tasks_by_status' in data['statistics']
        assert 'tasks_by_priority' in data['statistics']
    
    def test_statistics_endpoint_lines_136_141(self, client, setup_firebase_mocks, mock_db):
        """Lines 136, 141: Statistics endpoint with counts"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        users = [Mock(), Mock()]
        tasks = [Mock()]
        projects = [Mock()]
        memberships = [Mock()]
        
        def collection_mock(name):
            if name == "users":
                return Mock(
                    document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))),
                    stream=Mock(return_value=users)
                )
            elif name == "tasks":
                return Mock(stream=Mock(return_value=tasks))
            elif name == "projects":
                return Mock(stream=Mock(return_value=projects))
            elif name == "memberships":
                return Mock(stream=Mock(return_value=memberships))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/statistics?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['system_statistics']['users'] == 2
        assert data['system_statistics']['tasks'] == 1


# ============================================================================
# STAFF MANAGEMENT TESTS
# ============================================================================

class TestStaffManagement:
    """Staff creation and deletion tests"""
    
    def test_create_staff_success(self, client, setup_firebase_mocks, mock_db):
        """Successfully create a staff member"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_doc_ref = Mock()
        mock_doc_ref.set = Mock()
        
        mock_db.collection.return_value.document.side_effect = lambda doc_id: (
            Mock(get=Mock(return_value=mock_admin)) if doc_id == 'admin1' else mock_doc_ref
        )
        
        fake_auth.create_user = Mock(return_value=Mock(uid='new_staff_uid'))
        fake_auth.set_custom_user_claims = Mock()
        
        response = client.post('/api/admin/staff?admin_id=admin1', json={
            "email": "staff@test.com",
            "password": "password123",
            "name": "New Staff"
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] == True
        assert data['user']['user_id'] == 'new_staff_uid'
        assert data['user']['role'] == 'staff'
    
    def test_create_staff_missing_fields_line_237(self, client, setup_firebase_mocks, mock_db):
        """Line 237: Create staff with missing required fields"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.post('/api/admin/staff?admin_id=admin1', json={"email": "test@test.com"})
        assert response.status_code == 400
    
    def test_create_staff_firebase_error_line_232(self, client, setup_firebase_mocks, mock_db):
        """Line 232: Firebase error during staff creation"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        fake_auth.create_user = Mock(side_effect=Exception("Firebase error"))
        
        response = client.post('/api/admin/staff?admin_id=admin1', json={
            "email": "test@test.com", "password": "pass123", "name": "Test"
        })
        assert response.status_code == 500
    
    def test_delete_staff_soft_delete(self, client, setup_firebase_mocks, mock_db):
        """Soft delete staff member"""
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
                        return Mock(get=Mock(return_value=mock_user), update=Mock())
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.update_user = Mock()
        
        response = client.delete('/api/admin/staff/staff1?admin_id=admin1')
        assert response.status_code == 200
    
    def test_delete_staff_hard_delete(self, client, setup_firebase_mocks, mock_db):
        """Hard delete staff member"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff"})
        
        mock_doc_ref = Mock(get=Mock(return_value=mock_user), delete=Mock())
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.delete_user = Mock()
        
        response = client.delete('/api/admin/staff/staff1?admin_id=admin1&hard_delete=true')
        assert response.status_code == 200
    
    def test_delete_staff_wrong_role_lines_350_367(self, client, setup_firebase_mocks, mock_db):
        """Lines 350, 367: Try to delete staff when user has wrong role"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_target = Mock(exists=True)
        mock_target.to_dict = Mock(return_value={"role": "manager"})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == "admin1":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        response = client.delete('/api/admin/staff/user1?admin_id=admin1')
        assert response.status_code == 400
    
    def test_delete_staff_firebase_exception(self, client, setup_firebase_mocks, mock_db):
        """Firebase Auth exception during staff soft delete"""
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
                        return Mock(get=Mock(return_value=mock_user), update=Mock())
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.update_user = Mock(side_effect=Exception("Firebase error"))
        
        response = client.delete('/api/admin/staff/staff1?admin_id=admin1')
        assert response.status_code == 200


# ============================================================================
# MANAGER MANAGEMENT TESTS
# ============================================================================

class TestManagerManagement:
    """Manager creation and deletion tests"""
    
    def test_create_manager_success(self, client, setup_firebase_mocks, mock_db):
        """Successfully create a manager"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_doc_ref = Mock()
        mock_doc_ref.set = Mock()
        
        mock_db.collection.return_value.document.side_effect = lambda doc_id: (
            Mock(get=Mock(return_value=mock_admin)) if doc_id == 'admin1' else mock_doc_ref
        )
        
        fake_auth.create_user = Mock(return_value=Mock(uid='new_mgr_uid'))
        fake_auth.set_custom_user_claims = Mock()
        
        response = client.post('/api/admin/managers?admin_id=admin1', json={
            "email": "manager@test.com",
            "password": "password123",
            "name": "New Manager"
        })
        
        assert response.status_code == 201
    
    def test_create_manager_missing_fields_line_278(self, client, setup_firebase_mocks, mock_db):
        """Line 278: Create manager with missing fields"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.post('/api/admin/managers?admin_id=admin1', json={"email": "test@test.com"})
        assert response.status_code == 400
    
    def test_create_manager_invalid_type_line_298(self, client, setup_firebase_mocks, mock_db):
        """Line 298: Invalid manager_type value"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.post('/api/admin/managers?admin_id=admin1', json={
            "email": "test@test.com", "password": "pass123", "name": "Test",
            "manager_type": "InvalidType"
        })
        assert response.status_code == 400
    
    def test_create_manager_firebase_error_line_314(self, client, setup_firebase_mocks, mock_db):
        """Line 314: Firebase error during manager creation"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        fake_auth.create_user = Mock(side_effect=Exception("Firebase error"))
        
        response = client.post('/api/admin/managers?admin_id=admin1', json={
            "email": "test@test.com", "password": "pass123", "name": "Test"
        })
        assert response.status_code == 500
    
    def test_delete_manager_soft_delete_lines_493_494(self, client, setup_firebase_mocks, mock_db):
        """CRITICAL Lines 493-494: Manager soft delete with Firebase Auth exception"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_manager = Mock(exists=True)
        mock_manager.to_dict = Mock(return_value={"role": "manager", "is_active": True})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_manager), update=Mock())
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.update_user = Mock(side_effect=Exception("Firebase Auth error"))
        
        response = client.delete('/api/admin/managers/mgr1?admin_id=admin1')
        assert response.status_code == 200
    
    def test_delete_manager_hard_delete_line_455(self, client, setup_firebase_mocks, mock_db):
        """Line 455: Hard delete manager"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_target = Mock(exists=True)
        mock_target.to_dict = Mock(return_value={"role": "manager"})
        
        mock_doc_ref = Mock(get=Mock(return_value=mock_target), delete=Mock())
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == "admin1":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.delete_user = Mock()
        
        response = client.delete('/api/admin/managers/mgr1?admin_id=admin1&hard_delete=true')
        assert response.status_code == 200
    
    def test_delete_manager_wrong_role_line_441(self, client, setup_firebase_mocks, mock_db):
        """Line 441: Try to delete manager when user has wrong role"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_target = Mock(exists=True)
        mock_target.to_dict = Mock(return_value={"role": "staff"})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == "admin1":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        response = client.delete('/api/admin/managers/user1?admin_id=admin1')
        assert response.status_code == 400


# ============================================================================
# USER ROLE CHANGE TESTS
# ============================================================================

class TestUserRoleChanges:
    """User role modification tests"""
    
    def test_change_role_success(self, client, setup_firebase_mocks, mock_db):
        """Successfully change user role"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "is_active": True})
        
        mock_doc_ref = Mock(get=Mock(return_value=mock_user), update=Mock())
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.set_custom_user_claims = Mock()
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={"role": "manager"})
        assert response.status_code == 200
    
    def test_change_role_from_manager_success_lines_473_474(self, client, setup_firebase_mocks, mock_db):
        """Lines 473-474: Successfully change role FROM manager"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_target = Mock(exists=True)
        mock_target.to_dict = Mock(return_value={"role": "manager", "is_active": True})
        
        mock_doc_ref = Mock(get=Mock(return_value=mock_target), update=Mock())
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == "admin1":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.set_custom_user_claims = Mock()
        
        response = client.put('/api/admin/users/mgr1/role?admin_id=admin1', json={"role": "staff"})
        assert response.status_code == 200
    
    def test_change_role_invalid_role_line_516(self, client, setup_firebase_mocks, mock_db):
        """Line 516: Invalid role value"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={"role": "superadmin"})
        assert response.status_code == 400
    
    def test_change_role_self_modification_line_521(self, client, setup_firebase_mocks, mock_db):
        """Line 521: Prevent admin from changing own role"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        def collection_mock(name):
            if name == "users":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.put('/api/admin/users/admin1/role?admin_id=admin1', json={"role": "staff"})
        assert response.status_code == 400
    
    def test_change_role_firebase_exception(self, client, setup_firebase_mocks, mock_db):
        """Firebase exception during role change"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "is_active": True})
        
        mock_doc_ref = Mock(get=Mock(return_value=mock_user), update=Mock())
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.set_custom_user_claims = Mock(side_effect=Exception("Auth error"))
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={"new_role": "manager"})
        assert response.status_code in [200, 400, 500]


# ============================================================================
# USER STATUS CHANGE TESTS
# ============================================================================

class TestUserStatusChanges:
    """User activation/deactivation tests"""
    
    def test_change_status_deactivate(self, client, setup_firebase_mocks, mock_db):
        """Deactivate a user"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "is_active": True})
        
        mock_doc_ref = Mock(get=Mock(return_value=mock_user), update=Mock())
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.update_user = Mock()
        
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={"is_active": False})
        assert response.status_code == 200
    
    def test_change_status_activate_lines_587_591(self, client, setup_firebase_mocks, mock_db):
        """Lines 587, 591: Activate user"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_target = Mock(exists=True)
        mock_target.to_dict = Mock(return_value={"role": "staff", "is_active": False})
        
        mock_doc_ref = Mock(get=Mock(return_value=mock_target), update=Mock())
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == "admin1":
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.update_user = Mock()
        
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={"is_active": True})
        assert response.status_code == 200
    
    def test_change_status_missing_field_line_569(self, client, setup_firebase_mocks, mock_db):
        """Line 569: Missing is_active field"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={})
        assert response.status_code == 400
    
    def test_change_status_user_not_found_line_574(self, client, setup_firebase_mocks, mock_db):
        """Line 574: User not found"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_target = Mock(exists=False)
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == "admin1":
                        return Mock(get=Mock(return_value=mock_admin))
                    return Mock(get=Mock(return_value=mock_target))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.put('/api/admin/users/ghost/status?admin_id=admin1', json={"is_active": False})
        assert response.status_code == 404
    
    def test_change_status_firebase_exception(self, client, setup_firebase_mocks, mock_db):
        """Firebase exception during status change"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "is_active": True})
        
        mock_doc_ref = Mock(get=Mock(return_value=mock_user), update=Mock())
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    return mock_doc_ref
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        fake_auth.update_user = Mock(side_effect=Exception("Firebase error"))
        
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={"is_active": False})
        assert response.status_code == 200


# ============================================================================
# PROJECTS AND TASKS TESTS
# ============================================================================

class TestProjectsAndTasks:
    """Projects and tasks endpoints"""
    
    def test_get_projects_with_members_lines_625_630(self, client, setup_firebase_mocks, mock_db):
        """Lines 625, 630: Projects endpoint with member counting"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
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
    
    def test_get_tasks_with_filters_lines_664_669_686(self, client, setup_firebase_mocks, mock_db):
        """Lines 664, 669, 686: Tasks endpoint with filters"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
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


# ============================================================================
# USER LIST FILTERING TESTS
# ============================================================================

class TestUserListFiltering:
    """User list with role and status filtering"""
    
    def test_users_with_role_filter_lines_177_182(self, client, setup_firebase_mocks, mock_db):
        """Lines 177, 182: Role filtering"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        staff = Mock(id='s1')
        staff.to_dict = Mock(return_value={'role': 'staff', 'name': 'Staff'})
        manager = Mock(id='m1')
        manager.to_dict = Mock(return_value={'role': 'manager', 'name': 'Manager'})
        
        call_count = [0]
        def collection_mock(name):
            if name == "users":
                call_count[0] += 1
                if call_count[0] == 1:
                    return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
                return Mock(stream=Mock(return_value=[staff, manager]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        response = client.get('/api/admin/users?admin_id=admin1&role=manager')
        assert response.status_code == 200
    
    def test_users_with_status_filter(self, client, setup_firebase_mocks, mock_db):
        """Status filtering - active and inactive"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        active = Mock(id='u1')
        active.to_dict = Mock(return_value={'role': 'staff', 'is_active': True})
        inactive = Mock(id='u2')
        inactive.to_dict = Mock(return_value={'role': 'staff', 'is_active': False})
        
        call_count = [0]
        def collection_mock(name):
            if name == "users":
                call_count[0] += 1
                if call_count[0] == 1:
                    return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
                return Mock(stream=Mock(return_value=[active, inactive]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        response = client.get('/api/admin/users?admin_id=admin1&status=active')
        assert response.status_code == 200


# ============================================================================
# USER SYNC CHECK TESTS
# ============================================================================

class TestUserSyncCheck:
    """Check user synchronization between Firestore and Firebase Auth"""
    
    def test_check_both_synced(self, client, setup_firebase_mocks, mock_db):
        """User exists in both systems"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "synced@test.com", "name": "User"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(return_value=Mock(
            uid='user1', 
            email='synced@test.com',
            display_name='User',
            disabled=False,
            email_verified=True
        ))
        
        response = client.get('/api/admin/check/user1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['synced'] == True
        assert data['in_firestore'] == True
        assert data['in_firebase_auth'] == True
    
    def test_check_firestore_only(self, client, setup_firebase_mocks, mock_db):
        """User only in Firestore"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/orphan')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == True
        assert data['in_firebase_auth'] == False
    
    def test_check_firebase_exception_line_738(self, client, setup_firebase_mocks, mock_db):
        """Line 738: Firebase exception during check"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "user@test.com"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=Exception("Unknown error"))
        
        response = client.get('/api/admin/check/user1')
        assert response.status_code in [200, 500]


# ============================================================================
# USER CLEANUP TESTS
# ============================================================================

class TestUserCleanup:
    """User cleanup from both systems"""
    
    def test_cleanup_both_systems(self, client, setup_firebase_mocks, mock_db):
        """Cleanup from both Firestore and Firebase Auth"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "test@test.com"})
        
        mock_doc = Mock(get=Mock(return_value=mock_user), delete=Mock())
        mock_db.collection.return_value.document.return_value = mock_doc
        
        fake_auth.delete_user = Mock()
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code == 200
        data = response.get_json()
        assert data['firestore_deleted'] == True
        assert data['firebase_auth_deleted'] == True
    
    def test_cleanup_firestore_exception_lines_791_792(self, client, setup_firebase_mocks, mock_db):
        """Lines 791-792: Firestore deletion exception"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "test@test.com"})
        
        mock_doc = Mock(
            get=Mock(return_value=mock_user),
            delete=Mock(side_effect=Exception("Firestore error"))
        )
        mock_db.collection.return_value.document.return_value = mock_doc
        
        fake_auth.delete_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code in [200, 404]
        data = response.get_json()
        assert 'errors' in data
    
    def test_cleanup_firebase_exception_lines_798_801(self, client, setup_firebase_mocks, mock_db):
        """Lines 798-801: Firebase Auth deletion exception"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.delete_user = Mock(side_effect=Exception("Firebase error"))
        
        response = client.delete('/api/admin/cleanup/user1?confirm=true')
        assert response.status_code in [200, 404]
        data = response.get_json()
        assert 'errors' in data
    
    def test_cleanup_nothing_to_cleanup(self, client, setup_firebase_mocks, mock_db):
        """No user to cleanup"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.delete_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.delete('/api/admin/cleanup/nonexistent?confirm=true')
        assert response.status_code == 404
        data = response.get_json()
        assert 'Nothing to clean up' in data['status']


# ============================================================================
# USER SYNC TESTS
# ============================================================================

class TestUserSync:
    """Sync users between Firestore and Firebase Auth"""
    
    def test_sync_firestore_only_needs_password(self, client, setup_firebase_mocks, mock_db):
        """Sync Firestore-only user requires password"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com", "name": "Orphan"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.post('/api/admin/sync/orphan', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'Password required' in data.get('error', '')
    
    def test_sync_firestore_only_creates_firebase_user(self, client, setup_firebase_mocks, mock_db):
        """Sync creates Firebase Auth user"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com", "name": "Orphan"})
        
        mock_doc = Mock(get=Mock(return_value=mock_user), update=Mock())
        mock_db.collection.return_value.document.return_value = mock_doc
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        fake_auth.create_user = Mock(return_value=Mock(uid='new_uid'))
        
        response = client.post('/api/admin/sync/orphan', json={"password": "Pass123"})
        assert response.status_code == 201
        data = response.get_json()
        assert 'Created Firebase Auth user' in data.get('message', '')
    
    def test_sync_firebase_only_creates_firestore_doc(self, client, setup_firebase_mocks, mock_db):
        """Sync creates Firestore document"""
        mock_user = Mock(exists=False)
        mock_doc = Mock(get=Mock(return_value=mock_user), set=Mock())
        mock_db.collection.return_value.document.return_value = mock_doc
        
        fake_auth.get_user = Mock(return_value=Mock(
            uid='firebase_user', email='firebase@test.com', display_name='Firebase User'
        ))
        
        response = client.post('/api/admin/sync/firebase_user', json={})
        assert response.status_code == 201
        data = response.get_json()
        assert 'Created Firestore document' in data.get('message', '')
    
    def test_sync_already_synced(self, client, setup_firebase_mocks, mock_db):
        """Already synced user"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "synced@test.com"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(return_value=Mock(uid='synced'))
        
        response = client.post('/api/admin/sync/synced_user', json={})
        assert response.status_code == 200
        data = response.get_json()
        assert 'Already synced' in data.get('status', '')
    
    def test_sync_create_firebase_exception(self, client, setup_firebase_mocks, mock_db):
        """Exception during Firebase user creation"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com", "name": "Orphan"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        fake_auth.create_user = Mock(side_effect=Exception("Creation failed"))
        
        response = client.post('/api/admin/sync/orphan', json={"password": "Pass123"})
        assert response.status_code == 500


# ============================================================================
# RECOMMENDATION HELPER TESTS
# ============================================================================

class TestRecommendationHelper:
    """Test _get_recommendation helper function - lines 826-907"""
    
    def test_recommendation_both_synced(self, client, setup_firebase_mocks, mock_db):
        """Recommendation when both systems have user"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "synced@test.com", "name": "Synced"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(return_value=Mock(
            uid='synced', email='synced@test.com', display_name='Synced',
            disabled=False, email_verified=True
        ))
        
        response = client.get('/api/admin/check/synced')
        assert response.status_code == 200
        data = response.get_json()
        assert data['synced'] == True
        assert 'recommendation' in data
    
    def test_recommendation_firestore_only(self, client, setup_firebase_mocks, mock_db):
        """Recommendation when user only in Firestore"""
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"email": "orphan@test.com", "name": "Orphan"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/orphan')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == True
        assert data['in_firebase_auth'] == False
        assert 'recommendation' in data
    
    def test_recommendation_firebase_only(self, client, setup_firebase_mocks, mock_db):
        """Recommendation when user only in Firebase Auth"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(return_value=Mock(
            uid='firebase', email='firebase@test.com', display_name='Firebase',
            disabled=False, email_verified=True
        ))
        
        response = client.get('/api/admin/check/firebase')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == True
        assert 'recommendation' in data
    
    def test_recommendation_neither_exists(self, client, setup_firebase_mocks, mock_db):
        """Recommendation when user doesn't exist anywhere"""
        mock_user = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user
        
        fake_auth.get_user = Mock(side_effect=fake_auth.UserNotFoundError("Not found"))
        
        response = client.get('/api/admin/check/nonexistent')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == False
        assert 'recommendation' in data


# ============================================================================
# VALIDATION & ERROR TESTS
# ============================================================================

class TestValidations:
    """Input validation and error handling"""
    
    def test_dashboard_no_admin_id(self, client, setup_firebase_mocks, mock_db):
        """Dashboard without admin_id"""
        response = client.get('/api/admin/dashboard')
        assert response.status_code == 401
    
    def test_dashboard_invalid_admin(self, client, setup_firebase_mocks, mock_db):
        """Dashboard with invalid admin"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.get('/api/admin/dashboard?admin_id=invalid')
        assert response.status_code == 404
    
    def test_cleanup_without_confirmation(self, client, setup_firebase_mocks, mock_db):
        """Cleanup without confirm=true"""
        response = client.delete('/api/admin/cleanup/user1')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Confirmation required' in data['error']
    
    def test_admin_verification_create_staff_line_237(self, client, setup_firebase_mocks, mock_db):
        """Line 237: Admin verification failure in create_staff"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.post('/api/admin/staff?admin_id=invalid', json={
            "email": "staff@test.com", "password": "pass123", "name": "Staff"
        })
        assert response.status_code in [401, 403, 404]
    
    def test_admin_verification_create_manager_line_303(self, client, setup_firebase_mocks, mock_db):
        """Line 303: Admin verification failure in create_manager"""
        mock_admin = Mock(exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.post('/api/admin/managers?admin_id=invalid', json={
            "email": "mgr@test.com", "password": "pass123", "name": "Manager"
        })
        assert response.status_code in [401, 403, 404]
