"""
Final push to 100% coverage - targeting remaining 25 lines
Lines: 136, 177, 182, 367, 372, 418-419, 441, 446, 473-474, 493-494, 516, 521, 543-549, 569, 574, 630, 669, 737-740
"""
import pytest
from unittest.mock import Mock, patch
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestFinalCoverageLines:
    """Laser-focused tests for exact remaining lines"""
    
    def test_line_136_statistics_calculation_exact(self, client, setup_firebase_mocks, mock_db):
        """Line 136: exact calculation line"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create exactly counted collections
        users = [Mock() for _ in range(10)]
        tasks = [Mock() for _ in range(20)]
        projects = [Mock() for _ in range(5)]
        memberships = [Mock() for _ in range(15)]
        
        call_counts = {}
        def coll_effect(name):
            call_counts[name] = call_counts.get(name, 0) + 1
            mock_coll = Mock()
            if name == "users":
                if call_counts[name] == 1:
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    mock_coll.stream = Mock(return_value=users)
            elif name == "projects":
                mock_coll.stream = Mock(return_value=projects)
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=tasks)
            elif name == "memberships":
                mock_coll.stream = Mock(return_value=memberships)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        response = client.get('/api/admin/statistics?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        # Verify calculations happened (line 136)
        assert data['system_statistics']['average_tasks_per_user'] == 2.0
        assert data['system_statistics']['average_members_per_project'] == 3.0
    
    def test_lines_177_182_both_continue_statements(self, client, setup_firebase_mocks, mock_db):
        """Lines 177, 182: both continue statements in user filtering"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create distinct users to trigger continues
        users = []
        for i in range(10):
            user = Mock(id=f'user{i}')
            if i % 3 == 0:
                user.to_dict = lambda i=i: {'user_id': f'user{i}', 'role': 'staff', 'is_active': True, 'name': f'Staff{i}'}
            elif i % 3 == 1:
                user.to_dict = lambda i=i: {'user_id': f'user{i}', 'role': 'manager', 'is_active': False, 'name': f'Manager{i}'}
            else:
                user.to_dict = lambda i=i: {'user_id': f'user{i}', 'role': 'admin', 'is_active': True, 'name': f'Admin{i}'}
            users.append(user)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                # First call is for admin verification
                if not hasattr(coll_effect, 'call_count'):
                    coll_effect.call_count = 0
                coll_effect.call_count += 1
                
                if coll_effect.call_count == 1:
                    mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
                else:
                    mock_coll.stream = Mock(return_value=users)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Test with role filter - should trigger line 177 continue
        response = client.get('/api/admin/users?admin_id=admin1&role=staff')
        assert response.status_code == 200
        data = response.get_json()
        # Should only get staff users (line 177 filtered others)
        assert all(u['role'] == 'staff' for u in data['users'])
        
        # Reset call count
        coll_effect.call_count = 0
        
        # Test with status filter - should trigger line 182 continue
        response = client.get('/api/admin/users?admin_id=admin1&status=inactive')
        assert response.status_code == 200
        data = response.get_json()
        # Should only get inactive users (line 182 filtered active ones)
        assert all(not u['is_active'] for u in data['users'])
    
    def test_lines_367_372_staff_validation(self, client, setup_firebase_mocks, mock_db):
        """Lines 367, 372: staff removal validation"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Test line 367: user not found
        mock_user_not_found = Mock(exists=False)
        
        def doc_effect_367(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user_not_found))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect_367)
        response = client.delete('/api/admin/staff/nonexistent?admin_id=admin1')
        assert response.status_code == 404
        assert b'User not found' in response.data
        
        # Test line 372: wrong role
        mock_user_wrong_role = Mock(exists=True, to_dict=lambda: {"role": "manager", "name": "Manager User"})
        
        def doc_effect_372(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user_wrong_role))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect_372)
        response = client.delete('/api/admin/staff/manager_user?admin_id=admin1')
        assert response.status_code == 400
        assert b'staff only' in response.data
    
    def test_lines_418_419_441_446_manager_validation(self, client, setup_firebase_mocks, mock_db):
        """Lines 418-419, 441, 446: manager removal validation"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Test lines 418-419: manager not found
        mock_user_not_found = Mock(exists=False)
        
        def doc_effect_418(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user_not_found))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect_418)
        response = client.delete('/api/admin/managers/nonexistent?admin_id=admin1')
        assert response.status_code == 404
        
        # Test lines 441, 446: wrong role (not a manager)
        mock_user_staff = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "Staff User"})
        
        def doc_effect_441(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user_staff))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect_441)
        response = client.delete('/api/admin/managers/staff_user?admin_id=admin1')
        assert response.status_code == 400
        assert b'managers only' in response.data
    
    def test_lines_473_474_493_494_role_change_validation(self, client, setup_firebase_mocks, mock_db):
        """Lines 473-474, 493-494: role change validation"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Test lines 473-474: user not found
        mock_user_not_found = Mock(exists=False)
        
        def doc_effect_473(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user_not_found))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect_473)
        response = client.put('/api/admin/users/nonexistent/role?admin_id=admin1', json={'role': 'manager'})
        assert response.status_code == 404
        
        # Test lines 493-494: invalid role
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "User"})
        
        def doc_effect_493(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect_493)
        response = client.put('/api/admin/users/user1/role?admin_id=admin1', json={'role': 'superadmin'})
        assert response.status_code == 400
        assert b'Invalid role' in response.data
    
    def test_lines_516_521_self_role_change(self, client, setup_firebase_mocks, mock_db):
        """Lines 516, 521: prevent admin from changing own role"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin", "name": "Admin User"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        response = client.put('/api/admin/users/admin1/role?admin_id=admin1', json={'role': 'staff'})
        assert response.status_code == 400
        assert b'Cannot change your own role' in response.data
    
    def test_lines_543_549_569_574_status_change_validation(self, client, setup_firebase_mocks, mock_db):
        """Lines 543-549, 569, 574: status change validation"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Test lines 543-549: user not found
        mock_user_not_found = Mock(exists=False)
        
        def doc_effect_543(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user_not_found))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect_543)
        response = client.put('/api/admin/users/nonexistent/status?admin_id=admin1', json={'is_active': False})
        assert response.status_code == 404
        
        # Test lines 569, 574: invalid is_active value (not boolean)
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff", "name": "User"})
        
        def doc_effect_569(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect_569)
        
        # Test with string value
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={'is_active': 'yes'})
        assert response.status_code == 400
        assert b'must be true or false' in response.data
        
        # Test with number value
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={'is_active': 1})
        assert response.status_code == 400
    
    def test_line_630_projects_loop_execution(self, client, setup_firebase_mocks, mock_db):
        """Line 630: for loop iteration over projects"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create multiple distinct projects
        projects = []
        for i in range(5):
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
                # Return mock memberships query
                mock_coll.where = Mock(return_value=Mock(stream=Mock(return_value=[Mock(), Mock()])))
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        response = client.get('/api/admin/projects?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['projects']) == 5
        # Verify member_count was calculated for each
        assert all('member_count' in p for p in data['projects'])
    
    def test_line_669_tasks_loop_execution(self, client, setup_firebase_mocks, mock_db):
        """Line 669: for loop iteration over tasks with filters"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # Create multiple distinct tasks
        tasks = []
        for i in range(8):
            task = Mock(id=f'task{i}')
            if i % 2 == 0:
                task.to_dict = lambda i=i: {'title': f'Task {i}', 'status': 'pending', 'priority': 'high'}
            else:
                task.to_dict = lambda i=i: {'title': f'Task {i}', 'status': 'done', 'priority': 'low'}
            tasks.append(task)
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=tasks)
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        
        # Test without filter - hits line 669
        response = client.get('/api/admin/tasks?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['tasks']) == 8
        
        # Test with status filter - hits line 669 and filter logic
        response = client.get('/api/admin/tasks?admin_id=admin1&status=pending')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['tasks']) == 4
        assert all(t['status'] == 'pending' for t in data['tasks'])
    
    def test_lines_737_740_sync_check_mismatch(self, client, setup_firebase_mocks, mock_db):
        """Lines 737-740: sync check when user only in Firebase"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        # User NOT in Firestore
        mock_user_firestore = Mock(exists=False)
        
        def doc_effect(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user_firestore))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        # User EXISTS in Firebase Auth
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
        
        # Verify sync status calculation (lines 737-740)
        assert data['in_firestore'] == False
        assert data['in_firebase_auth'] == True
        assert data['synced'] == False  # This is the key line 740
        assert 'firebase_data' in data
        assert data['firebase_data']['email'] == 'test@example.com'


class TestEdgeCasesCoverage:
    """Additional edge cases for complete coverage"""
    
    def test_status_change_with_none_value(self, client, setup_firebase_mocks, mock_db):
        """Test status change with None value"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        mock_user = Mock(exists=True, to_dict=lambda: {"role": "staff"})
        
        def doc_effect(doc_id):
            if doc_id == 'admin1':
                return Mock(get=Mock(return_value=mock_admin))
            else:
                return Mock(get=Mock(return_value=mock_user))
        
        mock_db.collection.return_value.document = Mock(side_effect=doc_effect)
        
        response = client.put('/api/admin/users/user1/status?admin_id=admin1', json={'is_active': None})
        assert response.status_code == 400
    
    def test_projects_with_zero_memberships(self, client, setup_firebase_mocks, mock_db):
        """Test project iteration with no memberships"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        proj = Mock(id='proj1')
        proj.to_dict = lambda: {'name': 'Empty Project'}
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "projects":
                mock_coll.stream = Mock(return_value=[proj])
            elif name == "memberships":
                # Zero memberships
                mock_coll.where = Mock(return_value=Mock(stream=Mock(return_value=[])))
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        response = client.get('/api/admin/projects?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['projects'][0]['member_count'] == 0
    
    def test_tasks_priority_filter_string_conversion(self, client, setup_firebase_mocks, mock_db):
        """Test tasks with priority filter and string conversion"""
        mock_admin = Mock(exists=True, to_dict=lambda: {"role": "admin"})
        
        task1 = Mock(id='t1')
        task1.to_dict = lambda: {'title': 'T1', 'priority': 1}  # Integer priority
        task2 = Mock(id='t2')
        task2.to_dict = lambda: {'title': 'T2', 'priority': '2'}  # String priority
        
        def coll_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document = Mock(return_value=Mock(get=Mock(return_value=mock_admin)))
            elif name == "tasks":
                mock_coll.stream = Mock(return_value=[task1, task2])
            return mock_coll
        
        mock_db.collection = Mock(side_effect=coll_effect)
        response = client.get('/api/admin/tasks?admin_id=admin1&priority=1')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['tasks']) == 1
