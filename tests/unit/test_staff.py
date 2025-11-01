"""
Unit tests for staff.py endpoints to achieve 100% coverage
"""
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
