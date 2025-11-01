"""
Final tests to achieve 100% coverage for backend/api/admin.py
Covers remaining 40 missing lines
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestAdmin100Coverage:
    """Tests to cover all remaining uncovered lines"""

    def test_dashboard_no_admin_id(self, client, setup_firebase_mocks):
        """Line 46: dashboard without admin_id"""
        response = client.get('/api/admin/dashboard')
        assert response.status_code == 401
        assert b'admin_id required' in response.data

    def test_statistics_calculations(self, client, setup_firebase_mocks, mock_db):
        """Line 136: statistics endpoint calculations"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_users = [Mock(id=f'u{i}', to_dict=lambda: {'role': 'staff'}) for i in range(5)]
        mock_projects = [Mock(id=f'p{i}', to_dict=lambda: {}) for i in range(3)]
        mock_tasks = [Mock(id=f't{i}', to_dict=lambda: {}) for i in range(7)]
        mock_memberships = [Mock(id=f'm{i}') for i in range(4)]
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                mock_coll.stream = Mock(return_value=mock_users)
            elif name == "projects":
                mock_coll.stream = Mock(return_value=mock_projects)
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=mock_tasks)
            elif name == "memberships":
                mock_coll.stream = Mock(return_value=mock_memberships)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        response = client.get('/api/admin/statistics?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert 'system_statistics' in data
        assert data['system_statistics']['users'] == 5
        assert data['system_statistics']['projects'] == 3
        assert data['system_statistics']['tasks'] == 7

    def test_users_role_filter_skip(self, client, setup_firebase_mocks, mock_db):
        """Line 177: skip user when role doesn't match"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_users = [
            Mock(id='u1', to_dict=lambda: {'role': 'staff', 'is_active': True, 'name': 'Staff'}),
            Mock(id='u2', to_dict=lambda: {'role': 'admin', 'is_active': True, 'name': 'Admin'}),
        ]
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                mock_coll.stream = Mock(return_value=mock_users)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        response = client.get('/api/admin/users?admin_id=admin1&role=staff')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 1
        assert data['users'][0]['role'] == 'staff'

    def test_users_status_filter_skip(self, client, setup_firebase_mocks, mock_db):
        """Line 182: skip user when status doesn't match"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_users = [
            Mock(id='u1', to_dict=lambda: {'role': 'staff', 'is_active': True, 'name': 'Active'}),
            Mock(id='u2', to_dict=lambda: {'role': 'staff', 'is_active': False, 'name': 'Inactive'}),
        ]
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                mock_coll.stream = Mock(return_value=mock_users)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        response = client.get('/api/admin/users?admin_id=admin1&status=active')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 1
        assert data['users'][0]['is_active'] == True

    def test_add_staff_success_full_flow(self, client, setup_firebase_mocks, mock_db):
        """Lines 258-271: successful staff creation"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        fake_user = Mock(uid='new_staff_uid')
        fake_auth.create_user = Mock(return_value=fake_user)
        
        response = client.post('/api/admin/staff?admin_id=admin1', json={
            'email': 'newstaff@test.com',
            'password': 'password123',
            'name': 'New Staff'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] == True
        assert data['user']['role'] == 'staff'

    def test_add_manager_success_full_flow(self, client, setup_firebase_mocks, mock_db):
        """Lines 330-343: successful manager creation"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        fake_user = Mock(uid='new_manager_uid')
        fake_auth.create_user = Mock(return_value=fake_user)
        
        response = client.post('/api/admin/managers?admin_id=admin1', json={
            'email': 'newmanager@test.com',
            'password': 'password123',
            'name': 'New Manager'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] == True
        assert 'Manager' in data['message']

    def test_remove_staff_not_exists(self, client, setup_firebase_mocks, mock_db):
        """Line 367: staff user doesn't exist"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=False)
        
        call_count = [0]
        def get_effect():
            call_count[0] += 1
            return mock_admin if call_count[0] == 1 else mock_user
        
        mock_db.collection.return_value.document.return_value.get = Mock(side_effect=get_effect)
        response = client.delete('/api/admin/staff/nonexistent?admin_id=admin1')
        assert response.status_code == 404

    def test_remove_staff_wrong_role_error(self, client, setup_firebase_mocks, mock_db):
        """Line 372: trying to remove non-staff via staff endpoint"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "manager"})
        
        call_count = [0]
        def get_effect():
            call_count[0] += 1
            return mock_admin if call_count[0] == 1 else mock_user
        
        mock_db.collection.return_value.document.return_value.get = Mock(side_effect=get_effect)
        response = client.delete('/api/admin/staff/user1?admin_id=admin1')
        assert response.status_code == 400
        assert b'staff only' in response.data

    def test_remove_staff_hard_delete_auth_fails(self, client, setup_firebase_mocks, mock_db):
        """Lines 398-399: hard delete with auth failure"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff"})
        
        call_count = [0]
        def get_effect():
            call_count[0] += 1
            return mock_admin if call_count[0] == 1 else mock_user
        
        mock_db.collection.return_value.document.return_value.get = Mock(side_effect=get_effect)
        fake_auth.delete_user = Mock(side_effect=Exception("Auth delete failed"))
        
        response = client.delete('/api/admin/staff/user1?admin_id=admin1&hard_delete=true')
        assert response.status_code == 200
        assert b'permanently deleted' in response.data

    def test_remove_manager_not_exists(self, client, setup_firebase_mocks, mock_db):
        """Lines 418-419: manager user doesn't exist"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=False)
        
        call_count = [0]
        def get_effect():
            call_count[0] += 1
            return mock_admin if call_count[0] == 1 else mock_user
        
        mock_db.collection.return_value.document.return_value.get = Mock(side_effect=get_effect)
        response = client.delete('/api/admin/managers/nonexistent?admin_id=admin1')
        assert response.status_code == 404

    def test_remove_manager_wrong_role_error(self, client, setup_firebase_mocks, mock_db):
        """Lines 441, 446: trying to remove non-manager via manager endpoint"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff"})
        
        call_count = [0]
        def get_effect():
            call_count[0] += 1
            return mock_admin if call_count[0] == 1 else mock_user
        
        mock_db.collection.return_value.document.return_value.get = Mock(side_effect=get_effect)
        response = client.delete('/api/admin/managers/user1?admin_id=admin1')
        assert response.status_code == 400
        assert b'managers only' in response.data

    def test_change_role_user_not_exists(self, client, setup_firebase_mocks, mock_db):
        """Lines 473-474: user doesn't exist for role change"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=False)
        
        call_count = [0]
        def get_effect():
            call_count[0] += 1
            return mock_admin if call_count[0] == 1 else mock_user
        
        mock_db.collection.return_value.document.return_value.get = Mock(side_effect=get_effect)
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={'role': 'manager'})
        assert response.status_code == 404

    def test_change_role_invalid_role_value(self, client, setup_firebase_mocks, mock_db):
        """Lines 493-494: invalid role provided"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff"})
        
        call_count = [0]
        def get_effect():
            call_count[0] += 1
            return mock_admin if call_count[0] == 1 else mock_user
        
        mock_db.collection.return_value.document.return_value.get = Mock(side_effect=get_effect)
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={'role': 'superuser'})
        assert response.status_code == 400
        assert b'Invalid role' in response.data

    def test_change_role_self_change(self, client, setup_firebase_mocks, mock_db):
        """Lines 516, 521: admin trying to change own role"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_db.collection.return_value.document.return_value.get = Mock(return_value=mock_admin)
        
        response = client.put('/api/admin/users/admin1/role?admin_id=admin1', json={'role': 'staff'})
        assert response.status_code == 400
        assert b'Cannot change your own role' in response.data

    def test_change_status_user_not_exists(self, client, setup_firebase_mocks, mock_db):
        """Lines 543-549: user doesn't exist for status change"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=False)
        
        call_count = [0]
        def get_effect():
            call_count[0] += 1
            return mock_admin if call_count[0] == 1 else mock_user
        
        mock_db.collection.return_value.document.return_value.get = Mock(side_effect=get_effect)
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={'is_active': False})
        assert response.status_code == 404

    def test_change_status_invalid_bool(self, client, setup_firebase_mocks, mock_db):
        """Lines 569, 574, 580: invalid is_active value"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff"})
        
        call_count = [0]
        def get_effect():
            call_count[0] += 1
            return mock_admin if call_count[0] == 1 else mock_user
        
        mock_db.collection.return_value.document.return_value.get = Mock(side_effect=get_effect)
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={'is_active': 'yes'})
        assert response.status_code == 400
        assert b'must be true or false' in response.data

    def test_get_projects_with_data(self, client, setup_firebase_mocks, mock_db):
        """Line 630: projects iteration"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_projects = [
            Mock(id='p1', to_dict=lambda: {'name': 'Project 1', 'status': 'active'}),
            Mock(id='p2', to_dict=lambda: {'name': 'Project 2', 'status': 'completed'})
        ]
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "projects":
                mock_coll.stream = Mock(return_value=mock_projects)
            elif name == "memberships":
                # Return empty list for memberships query
                mock_coll.where = Mock(return_value=Mock(stream=Mock(return_value=[])))
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        response = client.get('/api/admin/projects?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['projects']) == 2

    def test_get_tasks_with_filtering(self, client, setup_firebase_mocks, mock_db):
        """Line 669: tasks iteration and filtering"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_tasks = [
            Mock(id='t1', to_dict=lambda: {'title': 'Task 1', 'status': 'pending', 'priority': 'high'}),
            Mock(id='t2', to_dict=lambda: {'title': 'Task 2', 'status': 'completed', 'priority': 'low'}),
            Mock(id='t3', to_dict=lambda: {'title': 'Task 3', 'status': 'pending', 'priority': 'medium'})
        ]
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=mock_tasks)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        response = client.get('/api/admin/tasks?admin_id=admin1&status=pending')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['tasks']) == 2

    def test_check_sync_firebase_auth_only(self, client, setup_firebase_mocks, mock_db):
        """Lines 737-740: user in Firebase Auth but not Firestore"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=False)
        
        # Create separate mock documents for each call
        def doc_effect(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        fake_auth.get_user = Mock(return_value=Mock(
            uid='user1',
            email='user@test.com',
            display_name='Test User',
            disabled=False,
            email_verified=True
        ))
        
        response = client.get('/api/admin/check/user1?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == True
        assert data['synced'] == False

    def test_verify_admin_access_admin_not_in_db(self, client, setup_firebase_mocks):
        """Line 26: admin user not found in Firestore"""
        with patch('backend.api.admin.firestore.client') as mock_firestore:
            mock_db = Mock()
            mock_firestore.return_value = mock_db
            mock_admin_doc = Mock(exists=False)
            mock_db.collection.return_value.document.return_value.get.return_value = mock_admin_doc
            
            response = client.get('/api/admin/dashboard?admin_id=missing_admin')
            assert response.status_code == 404
            assert b'Admin user not found' in response.data

    def test_add_staff_missing_admin_id(self, client, setup_firebase_mocks):
        """Line 232: add staff without admin_id"""
        response = client.post('/api/admin/staff', json={
            'email': 'test@test.com',
            'password': 'password',
            'name': 'Test'
        })
        assert response.status_code == 401

    def test_add_staff_admin_check_fails(self, client, setup_firebase_mocks):
        """Line 237: add staff with non-admin user"""
        with patch('backend.api.admin.firestore.client') as mock_firestore:
            mock_db = Mock()
            mock_firestore.return_value = mock_db
            mock_admin_doc = Mock(exists=True, to_dict=lambda: {"role": "staff"})
            mock_db.collection.return_value.document.return_value.get.return_value = mock_admin_doc
            
            response = client.post('/api/admin/staff?admin_id=staff1', json={
                'email': 'test@test.com',
                'password': 'password',
                'name': 'Test'
            })
            assert response.status_code == 403

    def test_add_manager_missing_admin_id(self, client, setup_firebase_mocks):
        """Line 298: add manager without admin_id"""
        response = client.post('/api/admin/managers', json={
            'email': 'test@test.com',
            'password': 'password',
            'name': 'Test'
        })
        assert response.status_code == 401

    def test_add_manager_admin_check_fails(self, client, setup_firebase_mocks):
        """Line 303: add manager with non-admin user"""
        with patch('backend.api.admin.firestore.client') as mock_firestore:
            mock_db = Mock()
            mock_firestore.return_value = mock_db
            mock_admin_doc = Mock(exists=True, to_dict=lambda: {"role": "manager"})
            mock_db.collection.return_value.document.return_value.get.return_value = mock_admin_doc
            
            response = client.post('/api/admin/managers?admin_id=mgr1', json={
                'email': 'test@test.com',
                'password': 'password',
                'name': 'Test'
            })
            assert response.status_code == 403


class TestFinalLines:
    """Additional tests to hit final missing lines"""
    
    def test_users_both_filters_applied(self, client, setup_firebase_mocks, mock_db):
        """Lines 177, 182: both role and status filters"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create unique mock users
        u1 = Mock(id='u1')
        u1.to_dict = lambda: {'user_id': 'u1', 'role': 'staff', 'is_active': True, 'name': 'Active Staff'}
        u2 = Mock(id='u2')
        u2.to_dict = lambda: {'user_id': 'u2', 'role': 'manager', 'is_active': True, 'name': 'Active Manager'}
        u3 = Mock(id='u3')
        u3.to_dict = lambda: {'user_id': 'u3', 'role': 'staff', 'is_active': False, 'name': 'Inactive Staff'}
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                mock_coll.stream = Mock(return_value=[u1, u2, u3])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Test role filter alone
        response = client.get('/api/admin/users?admin_id=admin1&role=staff')
        assert response.status_code == 200
        data = response.get_json()
        # Should get both staff (active and inactive)
        assert len(data['users']) == 2
        
        # Test status filter alone
        response = client.get('/api/admin/users?admin_id=admin1&status=active')
        assert response.status_code == 200
        data = response.get_json()
        # Should get staff and manager (both active)
        assert len(data['users']) == 2

