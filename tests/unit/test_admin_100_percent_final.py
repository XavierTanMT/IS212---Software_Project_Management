"""
FINAL PUSH TO 100% - Covering last 22 lines with surgical precision
Lines: 136, 177, 182, 367, 372, 418-419, 441, 446, 473-474, 493-494, 516, 521, 543-549, 569, 574, 630, 669
"""
import pytest
from unittest.mock import Mock
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestLine136Statistics:
    """Line 136: round(tasks_count / users_count, 2) if users_count > 0 else 0"""
    
    def test_line_136_exact_division(self, client, setup_firebase_mocks, mock_db):
        """Execute the exact division on line 136"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create exactly 13 users, 39 tasks, 5 projects, 20 memberships
        users = [Mock() for _ in range(13)]
        tasks = [Mock() for _ in range(39)]
        projects = [Mock() for _ in range(5)]
        memberships = [Mock() for _ in range(20)]
        
        admin_verified = [False]
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                if not admin_verified[0]:
                    admin_verified[0] = True
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    mock_coll.stream = Mock(return_value=users)
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=tasks)
            elif name == "projects":
                mock_coll.stream = Mock(return_value=projects)
            elif name == "memberships":
                mock_coll.stream = Mock(return_value=memberships)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.get('/api/admin/statistics?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify line 136 executed: 39/13 = 3.0
        assert data['system_statistics']['average_tasks_per_user'] == 3.0
        # Also verify line for memberships/projects: 20/5 = 4.0
        assert data['system_statistics']['average_members_per_project'] == 4.0


class TestLines177And182UserFilters:
    """Lines 177, 182: continue statements in user filtering"""
    
    def test_line_177_role_filter_with_continue(self, client, setup_firebase_mocks, mock_db):
        """Line 177: if role_filter and user_data.get("role") != role_filter: continue"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create mix of roles to trigger continue
        user_staff1 = Mock(id='s1')
        user_staff1.to_dict = lambda: {'user_id': 's1', 'role': 'staff', 'name': 'Staff1', 'is_active': True}
        
        user_manager = Mock(id='m1')
        user_manager.to_dict = lambda: {'user_id': 'm1', 'role': 'manager', 'name': 'Manager1', 'is_active': True}
        
        user_staff2 = Mock(id='s2')
        user_staff2.to_dict = lambda: {'user_id': 's2', 'role': 'staff', 'name': 'Staff2', 'is_active': True}
        
        user_admin_other = Mock(id='a2')
        user_admin_other.to_dict = lambda: {'user_id': 'a2', 'role': 'admin', 'name': 'Admin2', 'is_active': True}
        
        admin_verified = [False]
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                if not admin_verified[0]:
                    admin_verified[0] = True
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    mock_coll.stream = Mock(return_value=[user_staff1, user_manager, user_staff2, user_admin_other])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Filter by role=staff should skip manager and admin (line 177)
        response = client.get('/api/admin/users?admin_id=admin1&role=staff')
        assert response.status_code == 200
        data = response.get_json()
        
        # Should only get staff users (manager and admin skipped via continue)
        assert len(data['users']) == 2
        assert all(u['role'] == 'staff' for u in data['users'])
    
    def test_line_182_status_filter_with_continue(self, client, setup_firebase_mocks, mock_db):
        """Line 182: if status_filter == 'active' and not user_data.get("is_active", True): continue"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Mix of active and inactive
        user_active1 = Mock(id='a1')
        user_active1.to_dict = lambda: {'user_id': 'a1', 'role': 'staff', 'name': 'Active1', 'is_active': True}
        
        user_inactive = Mock(id='i1')
        user_inactive.to_dict = lambda: {'user_id': 'i1', 'role': 'staff', 'name': 'Inactive', 'is_active': False}
        
        user_active2 = Mock(id='a2')
        user_active2.to_dict = lambda: {'user_id': 'a2', 'role': 'staff', 'name': 'Active2', 'is_active': True}
        
        admin_verified = [False]
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                if not admin_verified[0]:
                    admin_verified[0] = True
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    mock_coll.stream = Mock(return_value=[user_active1, user_inactive, user_active2])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Filter by status=active should skip inactive (line 182)
        response = client.get('/api/admin/users?admin_id=admin1&status=active')
        assert response.status_code == 200
        data = response.get_json()
        
        # Should only get active users (inactive skipped via continue)
        assert len(data['users']) == 2
        assert all(u['is_active'] == True for u in data['users'])


class TestStaffRemovalLines367And372:
    """Lines 367, 372: Staff removal validations"""
    
    def test_line_367_staff_not_found(self, client, setup_firebase_mocks, mock_db):
        """Line 367: return jsonify({"error": "User not found"}), 404"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_not_found))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.delete('/api/admin/staff/nonexistent_user?admin_id=admin1')
        assert response.status_code == 404
        assert b'User not found' in response.data
    
    def test_line_372_staff_wrong_role(self, client, setup_firebase_mocks, mock_db):
        """Line 372: return jsonify({"error": "Can only remove staff..."}), 400"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_manager_user = Mock(exists=True, to_dict=lambda: {"role": "manager", "name": "Manager User"})
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_manager_user))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.delete('/api/admin/staff/manager_user?admin_id=admin1')
        assert response.status_code == 400
        assert b'staff only' in response.data


class TestManagerRemovalLines418And419And441And446:
    """Lines 418-419, 441, 446: Manager removal validations"""
    
    def test_lines_418_419_manager_not_found(self, client, setup_firebase_mocks, mock_db):
        """Lines 418-419: Manager not found"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_not_found))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.delete('/api/admin/managers/nonexistent?admin_id=admin1')
        assert response.status_code == 404
    
    def test_lines_441_446_manager_wrong_role(self, client, setup_firebase_mocks, mock_db):
        """Lines 441, 446: Wrong role for manager removal"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_staff_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "Staff User"})
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_staff_user))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.delete('/api/admin/managers/staff_user?admin_id=admin1')
        assert response.status_code == 400
        assert b'managers only' in response.data


class TestRoleChangeLines473And494And516And521:
    """Lines 473-474, 493-494, 516, 521: Role change validations"""
    
    def test_lines_473_474_role_change_user_not_found(self, client, setup_firebase_mocks, mock_db):
        """Lines 473-474: User not found for role change"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_not_found))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.put('/api/admin/users/nonexistent/role?admin_id=admin1', json={'role': 'manager'})
        assert response.status_code == 404
    
    def test_lines_493_494_invalid_role_value(self, client, setup_firebase_mocks, mock_db):
        """Lines 493-494: Invalid role value"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "User"})
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_user))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={'role': 'superuser'})
        assert response.status_code == 400
        assert b'Invalid role' in response.data
    
    def test_lines_516_521_prevent_self_role_change(self, client, setup_firebase_mocks, mock_db):
        """Lines 516, 521: Prevent admin from changing own role"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin", "name": "Admin"})
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/admin1/role?admin_id=admin1', json={'role': 'staff'})
        assert response.status_code == 400
        assert b'Cannot change your own role' in response.data


class TestStatusChangeLines543To574:
    """Lines 543-549, 569, 574: Status change validations"""
    
    def test_lines_543_to_549_status_user_not_found(self, client, setup_firebase_mocks, mock_db):
        """Lines 543-549: User not found for status change"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_not_found = Mock(exists=False)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_not_found))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.put('/api/admin/users/nonexistent/status?admin_id=admin1', json={'is_active': False})
        assert response.status_code == 404
    
    def test_lines_569_574_non_boolean_is_active(self, client, setup_firebase_mocks, mock_db):
        """Lines 569, 574: if not isinstance(is_active, bool)"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "User"})
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_user))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Test with string (not boolean)
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={'is_active': 'false'})
        assert response.status_code == 400
        assert b'must be true or false' in response.data
    
    def test_lines_569_574_integer_is_active(self, client, setup_firebase_mocks, mock_db):
        """Lines 569, 574: Test with integer (also not boolean)"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "User"})
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                def doc_effect(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_user))
                mock_coll.document = Mock(side_effect=doc_effect)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Test with integer (not boolean)
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={'is_active': 1})
        assert response.status_code == 400


class TestLine630ProjectsLoop:
    """Line 630: for project_doc in projects_query"""
    
    def test_line_630_multiple_projects_iteration(self, client, setup_firebase_mocks, mock_db):
        """Line 630: Iterate through multiple projects"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create 8 distinct projects
        projects = []
        for i in range(8):
            proj = Mock(id=f'proj{i}')
            proj.to_dict = lambda i=i: {'project_id': f'proj{i}', 'name': f'Project {i}', 'status': 'active'}
            projects.append(proj)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "projects":
                mock_coll.stream = Mock(return_value=projects)
            elif name == "memberships":
                # Return 4 members for each project
                mock_coll.where = Mock(return_value=Mock(stream=Mock(return_value=[Mock(), Mock(), Mock(), Mock()])))
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        response = client.get('/api/admin/projects?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # Should iterate all 8 projects (line 630)
        assert len(data['projects']) == 8
        assert all('member_count' in p for p in data['projects'])
        assert all(p['member_count'] == 4 for p in data['projects'])


class TestLine669TasksLoop:
    """Line 669: for task_doc in tasks_query"""
    
    def test_line_669_multiple_tasks_iteration(self, client, setup_firebase_mocks, mock_db):
        """Line 669: Iterate through multiple tasks"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create 12 distinct tasks
        tasks = []
        for i in range(12):
            task = Mock(id=f'task{i}')
            task.to_dict = lambda i=i: {
                'task_id': f'task{i}',
                'title': f'Task {i}',
                'status': 'pending' if i % 2 == 0 else 'done',
                'priority': 'high' if i < 6 else 'low'
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
        
        # Test without filters - should iterate all tasks (line 669)
        response = client.get('/api/admin/tasks?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # Should get all 12 tasks (line 669 iterated through all)
        assert len(data['tasks']) == 12
    
    def test_line_669_with_filters(self, client, setup_firebase_mocks, mock_db):
        """Line 669: Iterate with status and priority filters"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create tasks with different statuses and priorities
        tasks = []
        for i in range(10):
            task = Mock(id=f'task{i}')
            task.to_dict = lambda i=i: {
                'task_id': f'task{i}',
                'title': f'Task {i}',
                'status': 'pending' if i % 3 == 0 else 'done',
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
        
        # Test with status filter
        response = client.get('/api/admin/tasks?admin_id=admin1&status=pending')
        assert response.status_code == 200
        data = response.get_json()
        
        # Should filter properly after iteration
        assert all(t['status'] == 'pending' for t in data['tasks'])
