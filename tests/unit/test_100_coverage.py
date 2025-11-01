"""
Comprehensive tests to achieve 100% unit test coverage
This file targets all missing coverage in admin.py, manager.py, dashboard.py, and app.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import sys
import os

# Get fake modules from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")
fake_auth = sys.modules.get("firebase_admin.auth")
UserNotFoundError = fake_auth.UserNotFoundError if fake_auth else Exception

from flask import Flask
from backend.api import admin_bp, manager_bp, dashboard_bp


# ========== DASHBOARD.PY EDGE CASES ==========

class TestDashboardCoverage:
    """Tests to cover remaining dashboard.py lines"""
    
    def test_task_to_json_non_string_non_int_priority(self, client, mock_db, monkeypatch):
        """Test priority that is neither string nor int (line 18)"""
        from backend.api.dashboard import task_to_json
        
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_task.to_dict.return_value = {
            "title": "Test Task",
            "priority": None,  # Neither string nor int
            "status": "To Do"
        }
        
        result = task_to_json(mock_task)
        assert result["priority"] == "Medium"
    
    def test_enrich_task_invalid_due_date_type(self, client):
        """Test enrich_task with non-string, non-datetime due_date (lines 58-61)"""
        from backend.api.dashboard import enrich_task_with_timeline_status
        
        task = {
            "task_id": "task-123",
            "title": "Test",
            "status": "To Do",
            "due_date": 12345  # Integer, invalid type
        }
        
        result = enrich_task_with_timeline_status(task)
        assert result["timeline_status"] == "invalid_date"
        assert result["is_overdue"] is False
    
    def test_enrich_task_invalid_date_string(self, client):
        """Test enrich_task with invalid date string (line 64)"""
        from backend.api.dashboard import enrich_task_with_timeline_status
        
        task = {
            "task_id": "task-456",
            "title": "Test",
            "status": "To Do",
            "due_date": "not-a-date"
        }
        
        result = enrich_task_with_timeline_status(task)
        assert result["timeline_status"] == "invalid_date"
    
    def test_enrich_task_datetime_object(self, client):
        """Test enrich_task with datetime object (line 54)"""
        from backend.api.dashboard import enrich_task_with_timeline_status
        
        future_date = datetime.now(timezone.utc) + timedelta(days=10)
        task = {
            "task_id": "task-789",
            "title": "Test",
            "status": "To Do",
            "due_date": future_date
        }
        
        result = enrich_task_with_timeline_status(task)
        assert result["timeline_status"] == "future"
    
    def test_detect_conflicts_datetime_object(self, client):
        """Test detect_conflicts with datetime objects (line 128)"""
        from backend.api.dashboard import detect_conflicts
        
        date1 = datetime(2025, 12, 25, 10, 0, tzinfo=timezone.utc)
        date2 = datetime(2025, 12, 25, 14, 0, tzinfo=timezone.utc)
        
        tasks = [
            {"task_id": "1", "title": "T1", "due_date": date1},
            {"task_id": "2", "title": "T2", "due_date": date2}
        ]
        
        conflicts = detect_conflicts(tasks)
        assert len(conflicts) == 1
        assert conflicts[0]["count"] == 2
    
    def test_detect_conflicts_invalid_type(self, client):
        """Test detect_conflicts skips invalid types (line 131)"""
        from backend.api.dashboard import detect_conflicts
        
        tasks = [
            {"task_id": "1", "title": "T1", "due_date": "2025-12-25"},
            {"task_id": "2", "title": "T2", "due_date": 12345},  # Invalid
            {"task_id": "3", "title": "T3", "due_date": ["date"]}  # Invalid
        ]
        
        conflicts = detect_conflicts(tasks)
        assert len(conflicts) == 0  # Only 1 valid task


# ========== APP.PY EDGE CASES ==========

class TestAppCoverage:
    """Tests to cover remaining app.py lines"""
    
    @patch('backend.app.firebase_admin')
    @patch('backend.app.os.path.exists')
    @patch.dict(os.environ, {}, clear=True)
    def test_init_firebase_emulator_without_gcloud(self, mock_exists, mock_firebase):
        """Test emulator mode sets GCLOUD_PROJECT (lines 41-42)"""
        from backend.app import init_firebase
        
        os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
        mock_firebase._apps = {}
        mock_firebase.initialize_app = MagicMock()
        mock_exists.return_value = True
        
        result = init_firebase()
        
        assert os.environ.get("GCLOUD_PROJECT") == "demo-no-project"
        assert result is True
    
    @patch('backend.app.firebase_admin')
    @patch('backend.app.os.path.exists')
    @patch.dict(os.environ, {}, clear=True)
    def test_init_firebase_emulator_find_dummy_creds(self, mock_exists, mock_firebase):
        """Test emulator finds dummy credentials (line 52, 56)"""
        from backend.app import init_firebase
        
        os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
        mock_firebase._apps = {}
        mock_firebase.initialize_app = MagicMock()
        
        def exists_side_effect(path):
            return "dummy-credentials.json" in path
        
        mock_exists.side_effect = exists_side_effect
        
        result = init_firebase()
        
        assert "GOOGLE_APPLICATION_CREDENTIALS" in os.environ
        assert result is True
    
    @patch('backend.app.firebase_admin')
    @patch.dict(os.environ, {}, clear=True)
    def test_init_firebase_emulator_error(self, mock_firebase):
        """Test emulator initialization error (line 63, 67)"""
        from backend.app import init_firebase
        
        os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
        mock_firebase._apps = {}
        mock_firebase.initialize_app = MagicMock(side_effect=Exception("Init error"))
        
        result = init_firebase()
        
        assert result is False
    
    @patch('backend.app.firebase_admin')
    @patch('backend.app.get_firebase_credentials')
    @patch.dict(os.environ, {}, clear=True)
    def test_init_firebase_cloud_value_error(self, mock_get_creds, mock_firebase):
        """Test cloud mode ValueError (lines 85-87)"""
        from backend.app import init_firebase
        
        mock_get_creds.side_effect = ValueError("No credentials")
        mock_firebase._apps = {}
        
        result = init_firebase()
        
        assert result is False


# ========== EMULATOR ALREADY INITIALIZED TEST ==========

    @patch('backend.app.firebase_admin')
    @patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "localhost:8080"}, clear=True)
    def test_init_firebase_emulator_already_initialized(self, mock_firebase):
        """Test emulator mode when Firebase is already initialized (line 63)"""
        from backend.app import init_firebase
        
        # Mock Firebase as already initialized
        mock_firebase._apps = ["fake_app"]  # Non-empty list means already initialized
        
        result = init_firebase()
        assert result is True


# ========== ADMIN.PY COMPREHENSIVE TESTS ==========

class TestAdminComprehensive:
    """Comprehensive tests for all admin.py endpoints"""
    
    def test_admin_dashboard_no_admin_id(self, client, monkeypatch):
        """Test admin dashboard without admin_id"""
        response = client.get("/api/admin/dashboard")
        assert response.status_code == 401
    
    def test_admin_dashboard_not_admin_role(self, client, mock_db, monkeypatch):
        """Test admin dashboard with non-admin user"""
        admin_id = "user123"
        
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"role": "staff"}  # Not admin
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(f"/api/admin/dashboard?admin_id={admin_id}")
        assert response.status_code == 403
    
    def test_admin_dashboard_success(self, client, mock_db, monkeypatch):
        """Test admin dashboard success"""
        admin_id = "admin123"
        
        # Mock admin user
        mock_admin_doc = Mock()
        mock_admin_doc.exists = True
        mock_admin_doc.to_dict.return_value = {"role": "admin", "name": "Admin"}
        
        # Mock collections with proper to_dict() returning dicts
        mock_users = []
        for i in range(5):
            u = Mock()
            u.id = f"user{i}"
            u.to_dict.return_value = {"name": f"User {i}", "role": "staff", "email": f"user{i}@test.com"}
            mock_users.append(u)
        
        mock_tasks = []
        for i in range(10):
            t = Mock()
            t.id = f"task{i}"
            t.to_dict.return_value = {"title": f"Task {i}", "status": "in_progress"}
            mock_tasks.append(t)
        
        mock_projects = []
        for i in range(3):
            p = Mock()
            p.id = f"proj{i}"
            p.to_dict.return_value = {"name": f"Project {i}"}
            mock_projects.append(p)

        def collection_side_effect(name):
            mock_collection = Mock()
            if name == "users":
                mock_collection.stream.return_value = mock_users
                mock_collection.document.return_value.get.return_value = mock_admin_doc
            elif name == "tasks":
                mock_collection.stream.return_value = mock_tasks
            elif name == "projects":
                mock_collection.stream.return_value = mock_projects
            return mock_collection
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(f"/api/admin/dashboard?admin_id={admin_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "statistics" in data


# ========== MANAGER.PY COMPREHENSIVE TESTS ==========

class TestManagerComprehensive:
    """Comprehensive tests for manager.py endpoints"""
    
    def test_manager_dashboard_success(self, client, mock_db, monkeypatch):
        """Test manager team-tasks endpoint with no projects (simplest case)"""
        manager_id = "mgr123"
        
        # Mock manager user
        mock_mgr_doc = Mock()
        mock_mgr_doc.exists = True
        mock_mgr_doc.to_dict.return_value = {
            "role": "manager",
            "name": "Manager",
            "user_id": manager_id
        }
        
        # Mock collections - manager has no projects (empty membership list)
        def collection_side_effect(name):
            mock_collection = Mock()
            if name == "users":
                mock_collection.document.return_value.get.return_value = mock_mgr_doc
            elif name == "memberships":
                # Empty memberships - manager has no projects, so returns empty response
                mock_collection.where.return_value.stream.return_value = []
            return mock_collection
        
        mock_db.collection.side_effect = collection_side_effect
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # When manager has no projects, endpoint returns empty data with 200
        response = client.get(f"/api/manager/team-tasks?viewer_id={manager_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["team_tasks"] == []
        assert data["team_members"] == []
        assert data["projects"] == []


# ========== ADDITIONAL COVERAGE TESTS ==========

class TestAdditionalCoverage:
    """Additional tests to ensure 100% coverage"""
    
    def test_admin_user_not_found(self, client, mock_db, monkeypatch):
        """Test admin endpoints with user not found"""
        admin_id = "nonexistent"
        
        mock_doc = Mock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(f"/api/admin/dashboard?admin_id={admin_id}")
        assert response.status_code == 404
    
    def test_create_app_firebase_fail(self):
        """Test app creation when Firebase fails"""
        with patch('backend.app.init_firebase', return_value=False):
            from backend.app import create_app
            app = create_app()
            assert app is not None
            
            with app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                data = response.get_json()
                assert data["firebase"] == "not configured"
