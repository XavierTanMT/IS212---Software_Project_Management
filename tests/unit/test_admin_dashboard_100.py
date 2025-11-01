"""
DASHBOARD COVERAGE - Lines 84-92, 99-101 and other missing lines
Target 100% coverage with dashboard and remaining endpoints
"""
import pytest
from unittest.mock import Mock
import sys

fake_auth = sys.modules.get("firebase_admin.auth")


class TestDashboardLoopCoverage:
    """Cover dashboard task and project loops"""
    
    def test_dashboard_with_multiple_tasks_and_statuses(self, client, setup_firebase_mocks, mock_db):
        """Lines 84-92: Task loop with status and priority breakdown"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin", "name": "Admin", "email": "admin@test.com", "is_active": True})
        
        # Create tasks with different statuses and priorities
        task1 = Mock(id='t1')
        task1.to_dict = Mock(return_value={'title': 'Task 1', 'status': 'To Do', 'priority': 5})
        
        task2 = Mock(id='t2')
        task2.to_dict = Mock(return_value={'title': 'Task 2', 'status': 'In Progress', 'priority': 3})
        
        task3 = Mock(id='t3')
        task3.to_dict = Mock(return_value={'title': 'Task 3', 'status': 'Done', 'priority': 1})
        
        task4 = Mock(id='t4')
        task4.to_dict = Mock(return_value={'title': 'Task 4', 'status': 'To Do', 'priority': 5})
        
        # Create projects
        project1 = Mock(id='p1')
        project1.to_dict = Mock(return_value={'name': 'Project 1', 'status': 'active'})
        
        project2 = Mock(id='p2')
        project2.to_dict = Mock(return_value={'name': 'Project 2', 'status': 'completed'})
        
        # Create users
        user1 = Mock(id='u1')
        user1.to_dict = Mock(return_value={'name': 'User 1', 'role': 'staff', 'is_active': True})
        
        def collection_mock(name):
            if name == "users":
                return Mock(
                    document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))),
                    stream=Mock(return_value=[user1])
                )
            elif name == "tasks":
                return Mock(stream=Mock(return_value=[task1, task2, task3, task4]))
            elif name == "projects":
                return Mock(stream=Mock(return_value=[project1, project2]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/dashboard?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify task status breakdown was calculated (lines 84-92)
        assert 'statistics' in data
        assert 'tasks_by_status' in data['statistics']
        assert 'tasks_by_priority' in data['statistics']
        
        # Verify projects were included (lines 99-101)
        assert 'all_projects' in data
        assert len(data['all_projects']) == 2
    
    def test_dashboard_with_varied_priorities(self, client, setup_firebase_mocks, mock_db):
        """Lines 84-92: Ensure priority breakdown is calculated"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin", "name": "Admin", "email": "admin@test.com", "is_active": True})
        
        # Create tasks with various priorities
        tasks = []
        for i in range(8):
            task = Mock(id=f't{i}')
            priority = [1, 2, 3, 4, 5, 1, 2, 3][i]
            task.to_dict = Mock(return_value={
                'title': f'Task {i}',
                'status': 'To Do',
                'priority': priority
            })
            tasks.append(task)
        
        def collection_mock(name):
            if name == "users":
                return Mock(
                    document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))),
                    stream=Mock(return_value=[])
                )
            elif name == "tasks":
                return Mock(stream=Mock(return_value=tasks))
            elif name == "projects":
                return Mock(stream=Mock(return_value=[]))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        response = client.get('/api/admin/dashboard?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify priority breakdown includes multiple priorities
        assert 'tasks_by_priority' in data['statistics']


class TestRemainingMissingLines:
    """Target specific remaining missing lines"""
    
    def test_line_278_user_list_with_filters(self, client, setup_firebase_mocks, mock_db):
        """Line 278: Additional filtering logic"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        # Create users
        users = []
        for i in range(5):
            user = Mock(id=f'u{i}')
            user.to_dict = Mock(return_value={
                'user_id': f'u{i}',
                'role': 'staff' if i % 2 == 0 else 'manager',
                'name': f'User {i}',
                'is_active': i % 3 != 0
            })
            users.append(user)
        
        call_count = [0]
        
        def collection_mock(name):
            if name == "users":
                call_count[0] += 1
                if call_count[0] == 1:
                    return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
                return Mock(stream=Mock(return_value=users))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Test with both filters
        response = client.get('/api/admin/users?admin_id=admin1&role=staff&status=active')
        assert response.status_code == 200
    
    def test_line_350_staff_creation_error_path(self, client, setup_firebase_mocks, mock_db):
        """Line 350: Error handling in staff creation"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        mock_db.collection.return_value.document.return_value.get.return_value = mock_admin
        
        # Test with missing required field
        response = client.post('/api/admin/staff?admin_id=admin1', json={})
        assert response.status_code == 400
    
    def test_line_686_tasks_with_no_filters(self, client, setup_firebase_mocks, mock_db):
        """Line 686: Tasks endpoint return statement"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        tasks = []
        for i in range(3):
            task = Mock(id=f't{i}')
            task.to_dict = Mock(return_value={'title': f'Task {i}', 'status': 'pending', 'priority': 'high'})
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
        assert len(data['tasks']) == 3
    
    def test_line_738_sync_check_firebase_error(self, client, setup_firebase_mocks, mock_db):
        """Line 738: Sync check when Firebase auth fails"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        mock_firestore_user = Mock(exists=True)
        mock_firestore_user.to_dict = Mock(return_value={
            "user_id": "test_user",
            "email": "test@example.com",
            "name": "Test User",
            "role": "staff"
        })
        
        def collection_mock(name):
            if name == "users":
                def doc_mock(doc_id):
                    if doc_id == 'admin1':
                        return Mock(get=Mock(return_value=mock_admin))
                    else:
                        return Mock(get=Mock(return_value=mock_firestore_user))
                return Mock(document=Mock(side_effect=doc_mock))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Mock Firebase Auth to raise exception
        fake_auth.get_user = Mock(side_effect=Exception("User not found in Firebase Auth"))
        
        response = client.get('/api/admin/check/test_user?admin_id=admin1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['in_firestore'] == True
        assert data['in_firebase_auth'] == False


class TestCompleteEndpointCoverage:
    """Ensure all endpoints are fully covered"""
    
    def test_projects_with_member_counts(self, client, setup_firebase_mocks, mock_db):
        """Line 630: Projects loop with member count calculation"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        # Create 5 projects
        projects = []
        for i in range(5):
            proj = Mock(id=f'p{i}')
            proj.to_dict = Mock(return_value={'name': f'Project {i}', 'status': 'active'})
            projects.append(proj)
        
        # Mock memberships
        memberships = [Mock(), Mock(), Mock()]
        
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
        # Verify member_count was calculated
        assert all('member_count' in p for p in data['projects'])
    
    def test_tasks_with_filtering_logic(self, client, setup_firebase_mocks, mock_db):
        """Line 669: Tasks loop with status/priority filters"""
        mock_admin = Mock(exists=True)
        mock_admin.to_dict = Mock(return_value={"role": "admin"})
        
        # Create tasks with various attributes
        tasks = []
        statuses = ['pending', 'done', 'in_progress', 'pending', 'done']
        priorities = ['high', 'low', 'medium', 'high', 'low']
        
        for i in range(5):
            task = Mock(id=f't{i}')
            task.to_dict = Mock(return_value={
                'title': f'Task {i}',
                'status': statuses[i],
                'priority': priorities[i]
            })
            tasks.append(task)
        
        def collection_mock(name):
            if name == "users":
                return Mock(document=Mock(return_value=Mock(get=Mock(return_value=mock_admin))))
            elif name == "tasks":
                return Mock(stream=Mock(return_value=tasks))
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_mock)
        
        # Test with status filter
        response = client.get('/api/admin/tasks?admin_id=admin1&status=pending')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['tasks']) == 2
        assert all(t['status'] == 'pending' for t in data['tasks'])
        
        # Test with priority filter
        response = client.get('/api/admin/tasks?admin_id=admin1&priority=high')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['tasks']) == 2
        assert all(t['priority'] == 'high' for t in data['tasks'])
