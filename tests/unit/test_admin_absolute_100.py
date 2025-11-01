"""
ABSOLUTE FINAL PUSH TO 100% - Integration-style tests for stubborn lines
Using direct app context to ensure coverage detection
"""
import pytest
from unittest.mock import Mock, MagicMock
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestCoverageGaps:
    """Tests designed to trigger exact missing lines with verified execution"""
    
    def test_user_list_role_filter_continue_line_177(self, client, setup_firebase_mocks, mock_db):
        """MUST hit line 177: continue when role doesn't match"""
        # Setup admin
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin", "name": "Admin"})
        
        # Create users with DIFFERENT roles
        user_manager = Mock(id='mgr1')
        user_manager.to_dict = Mock(return_value={
            'user_id': 'mgr1',
            'role': 'manager',  # This will NOT match filter
            'name': 'Manager User',
            'is_active': True
        })
        
        user_staff = Mock(id='staff1')
        user_staff.to_dict = Mock(return_value={
            'user_id': 'staff1',
            'role': 'staff',  # This WILL match filter
            'name': 'Staff User',
            'is_active': True
        })
        
        admin_called = [False]
        
        def collection_mock(name):
            if name == "users":
                mock_coll = Mock()
                if not admin_called[0]:
                    admin_called[0] = True
                    # First call is for admin verification
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    # Second call is for listing users
                    mock_coll.stream = Mock(return_value=[user_manager, user_staff])
                return mock_coll
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Request with role=staff filter - manager should be skipped via line 177
        response = client.get('/api/admin/users?admin_id=admin1&role=staff')
        
        assert response.status_code == 200
        data = response.get_json()
        # Only staff should be returned
        assert len(data['users']) == 1
        assert data['users'][0]['role'] == 'staff'
    
    def test_user_list_status_filter_continue_line_182(self, client, setup_firebase_mocks, mock_db):
        """MUST hit line 182: continue when status is active but we want inactive"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin", "name": "Admin"})
        
        # Create users with different statuses
        user_active = Mock(id='active1')
        user_active.to_dict = Mock(return_value={
            'user_id': 'active1',
            'role': 'staff',
            'name': 'Active User',
            'is_active': True  # This will NOT match inactive filter
        })
        
        user_inactive = Mock(id='inactive1')
        user_inactive.to_dict = Mock(return_value={
            'user_id': 'inactive1',
            'role': 'staff',
            'name': 'Inactive User',
            'is_active': False  # This WILL match inactive filter
        })
        
        admin_called = [False]
        
        def collection_mock(name):
            if name == "users":
                mock_coll = Mock()
                if not admin_called[0]:
                    admin_called[0] = True
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    mock_coll.stream = Mock(return_value=[user_active, user_inactive])
                return mock_coll
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Request inactive users - active should be skipped via line 182
        response = client.get('/api/admin/users?admin_id=admin1&status=inactive')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 1
        assert data['users'][0]['is_active'] == False
    
    def test_staff_removal_wrong_role_line_372(self, client, setup_firebase_mocks, mock_db):
        """MUST hit line 372: error when user is not staff"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_manager = Mock(exists=True)
        mock_manager.to_dict = Mock(return_value={"role": "manager", "name": "Manager"})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_manager))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.delete('/api/admin/staff/manager1?admin_id=admin1')
        assert response.status_code == 400
        assert b'staff only' in response.data
    
    def test_manager_not_found_lines_418_419(self, client, setup_firebase_mocks, mock_db):
        """MUST hit lines 418-419: manager not found"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_not_found = Mock(exists=False)
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_not_found))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.delete('/api/admin/managers/notfound?admin_id=admin1')
        assert response.status_code == 404
    
    def test_manager_removal_wrong_role_line_446(self, client, setup_firebase_mocks, mock_db):
        """MUST hit line 446: error when user is not manager"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_staff = Mock(exists=True)
        mock_staff.to_dict = Mock(return_value={"role": "staff", "name": "Staff"})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_staff))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.delete('/api/admin/managers/staff1?admin_id=admin1')
        assert response.status_code == 400
        assert b'managers only' in response.data
    
    def test_role_change_user_not_found_lines_473_474(self, client, setup_firebase_mocks, mock_db):
        """MUST hit lines 473-474: user not found for role change"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_not_found = Mock(exists=False)
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_not_found))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.put('/api/admin/users/notfound/role?admin_id=admin1', 
                            json={'role': 'manager'})
        assert response.status_code == 404
    
    def test_role_change_invalid_role_lines_493_494(self, client, setup_firebase_mocks, mock_db):
        """MUST hit lines 493-494: invalid role value"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "name": "User"})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_user))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', 
                            json={'role': 'superadmin'})
        assert response.status_code == 400
        assert b'Invalid role' in response.data
    
    def test_self_role_change_prevention_line_521(self, client, setup_firebase_mocks, mock_db):
        """MUST hit line 521: prevent admin from changing own role"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin", "name": "Admin"})
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/admin1/role?admin_id=admin1', 
                            json={'role': 'staff'})
        assert response.status_code == 400
        assert b'Cannot change your own role' in response.data
    
    def test_status_change_user_not_found_lines_543_to_549(self, client, setup_firebase_mocks, mock_db):
        """MUST hit lines 543-549: user not found for status change"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_not_found = Mock(exists=False)
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_not_found))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.put('/api/admin/users/notfound/status?admin_id=admin1', 
                            json={'is_active': False})
        assert response.status_code == 404
    
    def test_status_change_non_boolean_line_574(self, client, setup_firebase_mocks, mock_db):
        """MUST hit line 574: non-boolean is_active value"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_user = Mock(exists=True)
        mock_user.to_dict = Mock(return_value={"role": "staff", "name": "User"})
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_user))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Send string instead of boolean
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', 
                            json={'is_active': 'true'})
        assert response.status_code == 400
        assert b'must be true or false' in response.data
    
    def test_projects_loop_iteration_line_630(self, client, setup_firebase_mocks, mock_db):
        """MUST hit line 630: for loop over projects"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        # Create project docs
        project1 = Mock(id='p1')
        project1.to_dict = Mock(return_value={'name': 'Project 1', 'status': 'active'})
        
        project2 = Mock(id='p2')
        project2.to_dict = Mock(return_value={'name': 'Project 2', 'status': 'active'})
        
        project3 = Mock(id='p3')
        project3.to_dict = Mock(return_value={'name': 'Project 3', 'status': 'active'})
        
        def collection_mock(name):
            if name == "users":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
            elif name == "projects":
                return Mock(stream=Mock(return_value=[project1, project2, project3]))
            elif name == "memberships":
                # Return mock memberships for each project
                return Mock(where=Mock(return_value=Mock(stream=Mock(return_value=[Mock(), Mock()]))))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/projects?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['projects']) == 3
        # Verify member_count was calculated (proves loop executed)
        assert all('member_count' in p for p in data['projects'])
    
    def test_tasks_loop_iteration_line_669(self, client, setup_firebase_mocks, mock_db):
        """MUST hit line 669: for loop over tasks"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        # Create task docs
        task1 = Mock(id='t1')
        task1.to_dict = Mock(return_value={'title': 'Task 1', 'status': 'pending', 'priority': 'high'})
        
        task2 = Mock(id='t2')
        task2.to_dict = Mock(return_value={'title': 'Task 2', 'status': 'done', 'priority': 'low'})
        
        task3 = Mock(id='t3')
        task3.to_dict = Mock(return_value={'title': 'Task 3', 'status': 'pending', 'priority': 'medium'})
        
        task4 = Mock(id='t4')
        task4.to_dict = Mock(return_value={'title': 'Task 4', 'status': 'in_progress', 'priority': 'high'})
        
        def collection_mock(name):
            if name == "users":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
            elif name == "tasks":
                return Mock(stream=Mock(return_value=[task1, task2, task3, task4]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/tasks?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        # Should get all tasks (proves loop executed)
        assert len(data['tasks']) == 4
        assert all('title' in t for t in data['tasks'])


class TestForceExecutionPaths:
    """Additional tests with explicit execution path forcing"""
    
    def test_role_filter_forces_continue(self, client, setup_firebase_mocks, mock_db):
        """Force execution through role filter continue"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create 5 users with mixed roles
        users = []
        for i in range(5):
            u = Mock(id=f'u{i}')
            role = ['staff', 'manager', 'admin', 'staff', 'manager'][i]
            u.to_dict = lambda role=role, i=i: {
                'user_id': f'u{i}',
                'role': role,
                'name': f'User{i}',
                'is_active': True
            }
            users.append(u)
        
        calls = [0]
        def coll_eff(name):
            if name == "users":
                calls[0] += 1
                if calls[0] == 1:
                    return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
                return Mock(stream=Mock(return_value=users))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        # Filter for staff only
        response = client.get('/api/admin/users?admin_id=a1&role=staff')
        assert response.status_code == 200
        data = response.get_json()
        # Should get only 2 staff users
        assert len(data['users']) == 2
    
    def test_status_filter_forces_continue(self, client, setup_firebase_mocks, mock_db):
        """Force execution through status filter continue"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create users with mixed statuses
        users = []
        statuses = [True, False, True, False, True, False]
        for i in range(6):
            u = Mock(id=f'u{i}')
            u.to_dict = lambda i=i, active=statuses[i]: {
                'user_id': f'u{i}',
                'role': 'staff',
                'name': f'User{i}',
                'is_active': active
            }
            users.append(u)
        
        calls = [0]
        def coll_eff(name):
            if name == "users":
                calls[0] += 1
                if calls[0] == 1:
                    return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
                return Mock(stream=Mock(return_value=users))
            return Mock()
        
        mock_db.collection = Mock(side_effect=coll_eff)
        
        # Filter for active only
        response = client.get('/api/admin/users?admin_id=a1&status=active')
        assert response.status_code == 200
        data = response.get_json()
        # Should get only 3 active users
        assert len(data['users']) == 3
        assert all(u['is_active'] for u in data['users'])
