"""Unit tests for staff.py module"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import sys

# Get fake modules for mocking
fake_firestore = sys.modules.get("firebase_admin.firestore")


class TestStaffDashboard:
    def test_dashboard_project_doc_not_exists(self, client, mock_db, monkeypatch):
        """Test dashboard when project_doc.exists is False (branch coverage)"""
        user_id = "staff123"
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"name": "Staff User", "role": "staff"}

        mock_task1 = Mock()
        mock_task1.to_dict.return_value = {"title": "Task 1", "status": "in_progress"}
        mock_task1.id = "task1"
        mock_task2 = Mock()
        mock_task2.to_dict.return_value = {"title": "Task 2", "status": "to_do"}
        mock_task2.id = "task2"

        # Mock memberships
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": user_id}

        # Mock project (exists = False)
        mock_project_doc = Mock()
        mock_project_doc.exists = False

        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "tasks":
                mock_coll.where.return_value.stream.side_effect = [[mock_task1], [mock_task2]]
            elif name == "memberships":
                mock_coll.where.return_value.stream.return_value = [mock_membership]
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_project_doc
            return mock_coll

        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))

        response = client.get(f"/api/staff/dashboard?user_id={user_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data['view'] == 'staff'
        assert len(data['projects']) == 0  # No projects appended if exists is False
    """Test staff dashboard endpoint"""
    
    def test_dashboard_no_user_id(self, client):
        """Test dashboard without user_id"""
        response = client.get("/api/staff/dashboard")
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_dashboard_user_not_found(self, client, mock_db, monkeypatch):
        """Test dashboard with non-existent user"""
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/staff/dashboard?user_id=nonexistent")
        assert response.status_code == 404
    
    def test_dashboard_success(self, client, mock_db, monkeypatch):
        """Test successful staff dashboard"""
        user_id = "staff123"
        
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "name": "Staff User",
            "email": "staff@test.com",
            "role": "staff"
        }
        
        # Mock tasks created by user
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {"title": "Task 1", "status": "in_progress"}
        
        # Mock tasks assigned to user
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {"title": "Task 2", "status": "to_do"}
        
        # Mock memberships
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {"project_id": "proj1", "user_id": user_id}
        
        # Mock project
        mock_project_doc = Mock()
        mock_project_doc.exists = True
        mock_project_doc.to_dict.return_value = {"name": "Project 1", "description": "Test project"}
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "tasks":
                # First call is for created_by, second for assigned_to
                mock_coll.where.return_value.stream.side_effect = [[mock_task1], [mock_task2]]
            elif name == "memberships":
                mock_coll.where.return_value.stream.return_value = [mock_membership]
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_project_doc
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(f"/api/staff/dashboard?user_id={user_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data['view'] == 'staff'
        assert len(data['my_tasks']) == 1
        assert len(data['assigned_tasks']) == 1
        assert len(data['projects']) == 1
        assert data['statistics']['total_tasks'] == 2


class TestStaffGetTasks:
    """Test staff get tasks endpoint"""
    
    def test_get_tasks_no_user_id(self, client):
        """Test get tasks without user_id"""
        response = client.get("/api/staff/tasks")
        assert response.status_code == 400
    
    def test_get_tasks_success(self, client, mock_db, monkeypatch):
        """Test successful get tasks"""
        user_id = "staff123"
# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import staff as staff_module


class TestGetStaffDashboard:
    """Test the get_staff_dashboard endpoint"""
    
    def test_get_staff_dashboard_success(self, client, mock_db, monkeypatch):
        """Test staff dashboard returns correct data"""
        user_id = "staff123"
        current_user = {
            "user_id": user_id,
            "name": "John Doe",
            "email": "john@example.com"
        }
        
        # Mock tasks created by staff
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {
            "title": "My Task",
            "status": "In Progress",
            "created_by": {"user_id": user_id}
        }
        
        # Mock tasks assigned to staff
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {
            "title": "Assigned Task",
            "status": "To Do",
            "assigned_to": {"user_id": user_id}
        }
        
        # Mock membership
        mock_membership = Mock()
        mock_membership.to_dict.return_value = {
            "project_id": "proj1",
            "user_id": user_id
        }
        
        # Mock project
        mock_project = Mock()
        mock_project.exists = True
        mock_project.to_dict.return_value = {
            "name": "Test Project",
            "status": "active"
        }
        
        # Setup mock collection responses
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                # First call for created_by tasks
                mock_query.stream.side_effect = [[mock_task1], [mock_task2]]
                mock_coll.where.return_value = mock_query
                return mock_coll
            elif name == "memberships":
                mock_query = Mock()
                mock_query.stream.return_value = [mock_membership]
                mock_coll.where.return_value = mock_query
                return mock_coll
            elif name == "projects":
                mock_coll.document.return_value.get.return_value = mock_project
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Mock the decorator to pass through current_user
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.get('/staff/dashboard')
            
        assert response.status_code == 200
        data = response.get_json()
        assert data["view"] == "staff"
        assert "user" in data
        assert "my_tasks" in data
        assert "assigned_tasks" in data
        assert "projects" in data
        assert "statistics" in data
        assert data["statistics"]["my_tasks_count"] == 1
        assert data["statistics"]["assigned_tasks_count"] == 1
        assert data["statistics"]["projects_count"] == 1
        
    def test_get_staff_dashboard_no_tasks(self, client, mock_db, monkeypatch):
        """Test staff dashboard with no tasks"""
        user_id = "staff456"
        current_user = {
            "user_id": user_id,
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
        
        # Setup mock with empty collections
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                mock_query.stream.side_effect = [[], []]
                mock_coll.where.return_value = mock_query
                return mock_coll
            elif name == "memberships":
                mock_query = Mock()
                mock_query.stream.return_value = []
                mock_coll.where.return_value = mock_query
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.get('/staff/dashboard')
            
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["my_tasks"]) == 0
        assert len(data["assigned_tasks"]) == 0
        assert len(data["projects"]) == 0
        assert data["statistics"]["total_tasks"] == 0


class TestGetMyTasks:
    """Test the get_my_tasks endpoint"""
    
    def test_get_my_tasks_success(self, client, mock_db, monkeypatch):
        """Test getting staff member's own tasks"""
        user_id = "staff123"
        current_user = {
            "user_id": user_id,
            "name": "John Doe",
            "email": "john@example.com"
        }
        
        # Mock tasks
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict.return_value = {"title": "Task 1", "status": "in_progress"}
        
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {"title": "Task 2", "status": "to_do"}
        
        mock_coll = Mock()
        mock_coll.where.return_value.stream.return_value = [mock_task1, mock_task2]
        mock_db.collection.return_value = mock_coll
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(f"/api/staff/tasks?user_id={user_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert 'tasks' in data
        assert len(data['tasks']) == 2


class TestStaffCreateTask:
    """Test staff create task endpoint"""
    
    def test_create_task_no_user_id(self, client):
        """Test create task without user_id"""
        response = client.post(
            "/api/staff/tasks",
            json={"title": "New Task"}
        )
        assert response.status_code == 400
    
    def test_create_task_user_not_found(self, client, mock_db, monkeypatch):
        """Test create task with non-existent user"""
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            "/api/staff/tasks?user_id=nonexistent",
            json={"title": "New Task"}
        )
        assert response.status_code == 404
    
    def test_create_task_success(self, client, mock_db, monkeypatch):
        """Test successful task creation"""
        user_id = "staff123"
        
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "name": "Staff User",
            "email": "staff@test.com",
            "role": "staff"
        }
        
        # Mock task creation
        mock_task_ref = (None, Mock(id="new_task_123"))
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "tasks":
                mock_coll.add.return_value = mock_task_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post(
            f"/api/staff/tasks?user_id={user_id}",
            json={
                "title": "New Task",
                "description": "Test task",
                "priority": 3,
                "status": "To Do",
                "project_id": "proj1"
            }
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['task_id'] == "new_task_123"
    
    def test_create_task_with_defaults(self, client, mock_db, monkeypatch):
        """Test task creation uses default values"""
        user_id = "staff123"
        
        # Mock user document
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "name": "Staff User",
            "email": "staff@test.com",
            "role": "staff"
        }
        
        # Mock task creation
        mock_task_ref = (None, Mock(id="new_task_456"))
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "tasks":
                mock_coll.add.return_value = mock_task_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Create task with minimal data (tests default values)
        response = client.post(
            f"/api/staff/tasks?user_id={user_id}",
            json={"title": "Simple Task"}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        mock_task1.to_dict.return_value = {
            "title": "Task 1",
            "status": "In Progress",
            "created_by": {"user_id": user_id}
        }
        
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict.return_value = {
            "title": "Task 2",
            "status": "To Do",
            "created_by": {"user_id": user_id}
        }
        
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.stream.return_value = [mock_task1, mock_task2]
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.get('/staff/tasks')
            
        assert response.status_code == 200
        data = response.get_json()
        assert "tasks" in data
        assert len(data["tasks"]) == 2
        assert data["tasks"][0]["task_id"] == "task1"
        assert data["tasks"][1]["task_id"] == "task2"
        
    def test_get_my_tasks_empty(self, client, mock_db, monkeypatch):
        """Test getting tasks when staff has none"""
        user_id = "staff456"
        current_user = {
            "user_id": user_id,
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
        
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.stream.return_value = []
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.get('/staff/tasks')
            
        assert response.status_code == 200
        data = response.get_json()
        assert "tasks" in data
        assert len(data["tasks"]) == 0


class TestCreateTask:
    """Test the create_task endpoint"""
    
    def test_create_task_success(self, client, mock_db, monkeypatch):
        """Test staff successfully creates a task"""
        user_id = "staff123"
        current_user = {
            "user_id": user_id,
            "name": "John Doe",
            "email": "john@example.com"
        }
        
        task_data = {
            "title": "New Task",
            "description": "Task description",
            "priority": 7,
            "status": "To Do",
            "due_date": "2024-12-31T23:59:59+00:00",
            "project_id": "proj1",
            "labels": ["urgent"]
        }
        
        # Mock Firestore add response
        mock_doc_ref = Mock()
        mock_doc_ref.id = "new_task_123"
        mock_collection = Mock()
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.post('/staff/tasks', json=task_data)
            
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] == True
        assert data["task_id"] == "new_task_123"
        assert "message" in data
        
        # Verify task was added with correct data
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args[0][0]
        assert call_args["title"] == "New Task"
        assert call_args["description"] == "Task description"
        assert call_args["priority"] == 7
        assert call_args["status"] == "To Do"
        assert call_args["created_by"]["user_id"] == user_id
        assert call_args["created_by"]["name"] == "John Doe"
        assert "created_at" in call_args
        assert "updated_at" in call_args
        
    def test_create_task_with_defaults(self, client, mock_db, monkeypatch):
        """Test creating task with minimal data (defaults applied)"""
        user_id = "staff456"
        current_user = {
            "user_id": user_id,
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
        
        task_data = {
            "title": "Minimal Task"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "minimal_task_456"
        mock_collection = Mock()
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.post('/staff/tasks', json=task_data)
            
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] == True
        
        # Verify defaults were applied
        call_args = mock_collection.add.call_args[0][0]
        assert call_args["title"] == "Minimal Task"
        assert call_args["description"] == ""  # default
        assert call_args["priority"] == 5  # default
        assert call_args["status"] == "To Do"  # default
        assert call_args["labels"] == []  # default
        assert call_args["assigned_to"] == {}  # default
        
    def test_create_task_with_assigned_to(self, client, mock_db, monkeypatch):
        """Test creating task with assignee"""
        user_id = "staff789"
        current_user = {
            "user_id": user_id,
            "name": "Bob Smith",
            "email": "bob@example.com"
        }
        
        task_data = {
            "title": "Assigned Task",
            "assigned_to": {
                "user_id": "other_user",
                "name": "Other User",
                "email": "other@example.com"
            }
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "assigned_task_789"
        mock_collection = Mock()
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            response = client.post('/staff/tasks', json=task_data)
            
        assert response.status_code == 201
        
        # Verify assigned_to was included
        call_args = mock_collection.add.call_args[0][0]
        assert call_args["assigned_to"]["user_id"] == "other_user"
        assert call_args["assigned_to"]["name"] == "Other User"


class TestStaffEndpointsIntegration:
    """Integration tests for staff endpoints"""
    
    def test_staff_workflow_create_and_retrieve(self, client, mock_db, monkeypatch):
        """Test complete workflow: create task then retrieve it"""
        user_id = "staff_workflow"
        current_user = {
            "user_id": user_id,
            "name": "Workflow User",
            "email": "workflow@example.com"
        }
        
        # First, create a task
        task_data = {
            "title": "Workflow Task",
            "description": "Testing workflow",
            "status": "In Progress"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "workflow_task"
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                # For POST: add task
                mock_coll.add.return_value = (None, mock_doc_ref)
                
                # For GET: return the task
                mock_task = Mock()
                mock_task.id = "workflow_task"
                mock_task.to_dict.return_value = {
                    "title": "Workflow Task",
                    "description": "Testing workflow",
                    "status": "In Progress",
                    "created_by": {"user_id": user_id}
                }
                mock_query = Mock()
                mock_query.stream.return_value = [mock_task]
                mock_coll.where.return_value = mock_query
                
            return mock_coll
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.staff.firebase_required', lambda f: lambda *args, **kwargs: f(current_user, *args, **kwargs)):
            # Create task
            create_response = client.post('/staff/tasks', json=task_data)
            assert create_response.status_code == 201
            
            # Retrieve tasks
            get_response = client.get('/staff/tasks')
            assert get_response.status_code == 200
            data = get_response.get_json()
            assert len(data["tasks"]) == 1
            assert data["tasks"][0]["title"] == "Workflow Task"
