"""
Ultra-targeted tests for final 6% coverage - 25 lines
Targeting: 136, 177, 182, 367, 372, 418-419, 441, 446, 473-474, 493-494, 516, 521, 543-549, 569, 574, 630, 669, 737-740
"""
import pytest
from unittest.mock import Mock, patch
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestLine136StatisticsCalculation:
    """Line 136: average_tasks_per_user calculation"""
    
    def test_line_136_with_nonzero_users(self, client, setup_firebase_mocks, mock_db):
        """Test the exact division calculation on line 136"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Setup collections with specific counts
        users_list = [Mock() for _ in range(7)]
        tasks_list = [Mock() for _ in range(21)]
        projects_list = [Mock() for _ in range(3)]
        memberships_list = [Mock() for _ in range(12)]
        
        call_tracker = {'users': 0}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                call_tracker['users'] += 1
                if call_tracker['users'] == 1:
                    # First call is admin check
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    # Second call is for counting
                    mock_coll.stream = Mock(return_value=users_list)
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=tasks_list)
            elif name == "projects":
                mock_coll.stream = Mock(return_value=projects_list)
            elif name == "memberships":
                mock_coll.stream = Mock(return_value=memberships_list)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get('/api/admin/statistics?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify line 136 executed: average_tasks_per_user = round(tasks_count / users_count, 2)
        assert data['system_statistics']['average_tasks_per_user'] == 3.0  # 21/7 = 3.0
        assert data['system_statistics']['average_members_per_project'] == 4.0  # 12/3 = 4.0


class TestLines177And182Continues:
    """Lines 177, 182: continue statements in user list filters"""
    
    def test_line_177_role_filter_continue(self, client, setup_firebase_mocks, mock_db):
        """Line 177: continue when role doesn't match role_filter"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create users with different roles
        user1 = Mock(id='u1')
        user1.to_dict = lambda: {'user_id': 'u1', 'role': 'staff', 'name': 'Staff1', 'is_active': True}
        
        user2 = Mock(id='u2')
        user2.to_dict = lambda: {'user_id': 'u2', 'role': 'manager', 'name': 'Manager1', 'is_active': True}
        
        user3 = Mock(id='u3')
        user3.to_dict = lambda: {'user_id': 'u3', 'role': 'staff', 'name': 'Staff2', 'is_active': True}
        
        users_list = [user1, user2, user3]
        
        call_count = {'users': 0}
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                call_count['users'] += 1
                if call_count['users'] == 1:
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    mock_coll.stream = Mock(return_value=users_list)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Request with role filter - should hit line 177 continue for non-matching roles
        response = client.get('/api/admin/users?admin_id=admin1&role=staff')
        assert response.status_code == 200
        data = response.get_json()
        
        # Only staff users should be returned (manager was skipped via line 177)
        assert len(data['users']) == 2
        assert all(u['role'] == 'staff' for u in data['users'])
    
    def test_line_182_status_filter_continue(self, client, setup_firebase_mocks, mock_db):
        """Line 182: continue when status doesn't match status_filter"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create users with different statuses
        user1 = Mock(id='u1')
        user1.to_dict = lambda: {'user_id': 'u1', 'role': 'staff', 'name': 'Active', 'is_active': True}
        
        user2 = Mock(id='u2')
        user2.to_dict = lambda: {'user_id': 'u2', 'role': 'staff', 'name': 'Inactive', 'is_active': False}
        
        user3 = Mock(id='u3')
        user3.to_dict = lambda: {'user_id': 'u3', 'role': 'staff', 'name': 'Active2', 'is_active': True}
        
        users_list = [user1, user2, user3]
        
        call_count = {'users': 0}
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                call_count['users'] += 1
                if call_count['users'] == 1:
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    mock_coll.stream = Mock(return_value=users_list)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Request with status filter - should hit line 182 continue
        response = client.get('/api/admin/users?admin_id=admin1&status=inactive')
        assert response.status_code == 200
        data = response.get_json()
        
        # Only inactive users should be returned (active were skipped via line 182)
        assert len(data['users']) == 1
        assert data['users'][0]['is_active'] == False


class TestLines367And372StaffRemoval:
    """Lines 367, 372: staff removal endpoint validation"""
    
    def test_line_367_user_not_found(self, client, setup_firebase_mocks, mock_db):
        """Line 367: return error when user not found"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        call_count = {'doc': 0}
        
        def doc_effect(doc_id):
            call_count['doc'] += 1
            if call_count['doc'] == 1:
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_not_found))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        response = client.delete('/api/admin/staff/nonexist?admin_id=admin1')
        assert response.status_code == 404
        assert b'User not found' in response.data
    
    def test_line_372_wrong_role_for_staff_removal(self, client, setup_firebase_mocks, mock_db):
        """Line 372: return error when trying to remove non-staff as staff"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_manager = Mock(exists=True, to_dict=lambda: {"role": "manager", "name": "Manager"})
        
        call_count = {'doc': 0}
        
        def doc_effect(doc_id):
            call_count['doc'] += 1
            if call_count['doc'] == 1:
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_manager))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        response = client.delete('/api/admin/staff/manager1?admin_id=admin1')
        assert response.status_code == 400
        assert b'staff only' in response.data


class TestLines418And419And441And446ManagerRemoval:
    """Lines 418-419, 441, 446: manager removal endpoint validation"""
    
    def test_lines_418_419_manager_not_found(self, client, setup_firebase_mocks, mock_db):
        """Lines 418-419: return error when manager not found"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        call_count = {'doc': 0}
        
        def doc_effect(doc_id):
            call_count['doc'] += 1
            if call_count['doc'] == 1:
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_not_found))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        response = client.delete('/api/admin/managers/nonexist?admin_id=admin1')
        assert response.status_code == 404
    
    def test_lines_441_446_wrong_role_for_manager_removal(self, client, setup_firebase_mocks, mock_db):
        """Lines 441, 446: return error when trying to remove non-manager as manager"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_staff = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "Staff"})
        
        call_count = {'doc': 0}
        
        def doc_effect(doc_id):
            call_count['doc'] += 1
            if call_count['doc'] == 1:
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_staff))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        response = client.delete('/api/admin/managers/staff1?admin_id=admin1')
        assert response.status_code == 400
        assert b'managers only' in response.data


class TestLines473And474And493And494RoleChange:
    """Lines 473-474, 493-494: role change validation"""
    
    def test_lines_473_474_user_not_found_role_change(self, client, setup_firebase_mocks, mock_db):
        """Lines 473-474: return error when user not found"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        call_count = {'doc': 0}
        
        def doc_effect(doc_id):
            call_count['doc'] += 1
            if call_count['doc'] == 1:
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_not_found))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        response = client.put('/api/admin/users/nonexist/role?admin_id=admin1', json={'role': 'manager'})
        assert response.status_code == 404
    
    def test_lines_493_494_invalid_role_value(self, client, setup_firebase_mocks, mock_db):
        """Lines 493-494: return error when role value is invalid"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "User"})
        
        call_count = {'doc': 0}
        
        def doc_effect(doc_id):
            call_count['doc'] += 1
            if call_count['doc'] == 1:
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={'role': 'superuser'})
        assert response.status_code == 400
        assert b'Invalid role' in response.data


class TestLines516And521SelfRoleChange:
    """Lines 516, 521: prevent admin from changing own role"""
    
    def test_lines_516_521_self_role_change_prevention(self, client, setup_firebase_mocks, mock_db):
        """Lines 516, 521: prevent self role change"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin", "name": "Admin"})
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/admin1/role?admin_id=admin1', json={'role': 'staff'})
        assert response.status_code == 400
        assert b'Cannot change your own role' in response.data


class TestLines543To549And569And574StatusChange:
    """Lines 543-549, 569, 574: status change validation"""
    
    def test_lines_543_to_549_user_not_found_status(self, client, setup_firebase_mocks, mock_db):
        """Lines 543-549: user not found for status change"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        call_count = {'doc': 0}
        
        def doc_effect(doc_id):
            call_count['doc'] += 1
            if call_count['doc'] == 1:
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_not_found))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        response = client.put('/api/admin/users/nonexist/status?admin_id=admin1', json={'is_active': False})
        assert response.status_code == 404
    
    def test_lines_569_574_non_boolean_is_active(self, client, setup_firebase_mocks, mock_db):
        """Lines 569, 574: isinstance check for is_active"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "User"})
        
        call_count = {'doc': 0}
        
        def doc_effect(doc_id):
            call_count['doc'] += 1
            if call_count['doc'] == 1:
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        # Test with string (not boolean)
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={'is_active': 'false'})
        assert response.status_code == 400
        assert b'must be true or false' in response.data
        
        # Reset call count
        call_count['doc'] = 0
        
        # Test with integer (not boolean)
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={'is_active': 0})
        assert response.status_code == 400


class TestLine630ProjectsLoop:
    """Line 630: for loop over projects"""
    
    def test_line_630_projects_iteration(self, client, setup_firebase_mocks, mock_db):
        """Line 630: iterate over multiple projects"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create 6 distinct projects
        projects = []
        for i in range(6):
            proj = Mock(id=f'proj{i}')
            proj.to_dict = lambda i=i: {'name': f'Project {i}', 'status': 'active'}
            projects.append(proj)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "projects":
                mock_coll.stream = Mock(return_value=projects)
            elif name == "memberships":
                # Return 3 members per project
                mock_coll.where = Mock(return_value=Mock(stream=Mock(return_value=[Mock(), Mock(), Mock()])))
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.get('/api/admin/projects?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify all projects were iterated (line 630)
        assert len(data['projects']) == 6
        # Each should have member_count calculated
        assert all(p['member_count'] == 3 for p in data['projects'])


class TestLine669TasksLoop:
    """Line 669: for loop over tasks"""
    
    def test_line_669_tasks_iteration(self, client, setup_firebase_mocks, mock_db):
        """Line 669: iterate over multiple tasks"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create 10 distinct tasks
        tasks = []
        for i in range(10):
            task = Mock(id=f'task{i}')
            task.to_dict = lambda i=i: {
                'title': f'Task {i}',
                'status': 'pending' if i % 2 == 0 else 'done',
                'priority': 'high' if i < 5 else 'low'
            }
            tasks.append(task)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=tasks)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Test without filters - should iterate all
        response = client.get('/api/admin/tasks?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # All tasks should be returned (line 669 iterated through all)
        assert len(data['tasks']) == 10


class TestLines737To740SyncCheck:
    """Lines 737-740: sync check calculation"""
    
    def test_lines_737_740_user_in_firebase_not_firestore(self, client, setup_firebase_mocks, mock_db):
        """Lines 737-740: synced = in_firestore == in_firebase_auth"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_firestore_not_exists = Mock(exists=False)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_firestore_not_exists))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # User exists in Firebase Auth
        mock_firebase_user = Mock(
            uid='test_user',
            email='test@example.com',
            display_name='Test User',
            disabled=False,
            email_verified=True
        )
        fake_auth.get_user = Mock(return_value=mock_firebase_user)
        
        response = client.get('/api/admin/check/test_user?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify sync calculation (lines 737-740)
        # in_firestore = False, in_firebase_auth = True
        # synced = False == True = False
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == True
        assert data['synced'] == False
    
    def test_lines_737_740_user_in_firestore_not_firebase(self, client, setup_firebase_mocks, mock_db):
        """Lines 737-740: opposite case - in Firestore but not Firebase"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_firestore_user = Mock(exists=True, to_dict=lambda: {
            "user_id": "test_user",
            "email": "test@example.com",
            "name": "Test User",
            "role": "staff"
        })
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_firestore_user))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # User does NOT exist in Firebase Auth
        fake_auth.get_user = Mock(side_effect=Exception("User not found"))
        
        response = client.get('/api/admin/check/test_user?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify sync calculation (lines 737-740)
        # in_firestore = True, in_firebase_auth = False
        # synced = True == False = False
        assert data['in_firestore'] == True
        assert data['in_firebase_auth'] == False
        assert data['synced'] == False
