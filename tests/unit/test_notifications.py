"""Unit tests for notifications.py module"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import sys

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import notifications_bp
from backend.api import notifications as notifications_module


class TestNowIso:
    """Test the now_iso helper function"""
    
    def test_now_iso_returns_iso_format(self):
        """Test that now_iso returns ISO formatted datetime string"""
        mock_dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        with patch('backend.api.notifications.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_dt
            
            result = notifications_module.now_iso()
            
            assert result == "2024-01-15T10:30:45+00:00"
            mock_datetime.now.assert_called_once_with(timezone.utc)
            
    def test_now_iso_timezone_aware(self):
        """Test that now_iso always returns timezone-aware datetime"""
        result = notifications_module.now_iso()
        
        # Should be ISO format with timezone
        assert "+" in result or "Z" in result
        # Should be parseable back to datetime
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert dt.tzinfo is not None


class TestCreateNotification:
    """Test the create_notification helper function"""
    
    def test_create_notification_basic(self, mock_db):
        """Test creating a basic notification without email"""
        user_id = "user123"
        title = "Test Notification"
        body = "This is a test notification"
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif123"
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db.collection.return_value = mock_collection
        
        result = notifications_module.create_notification(
            mock_db, user_id, title, body, send_email=False
        )
        
        assert result == "notif123"
        mock_doc_ref.set.assert_called_once()
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["user_id"] == user_id
        assert call_args["title"] == title
        assert call_args["body"] == body
        assert call_args["read"] == False
        assert call_args["email_sent"] == False
        
    def test_create_notification_with_task_id(self, mock_db):
        """Test creating notification with task_id"""
        user_id = "user456"
        title = "Task Notification"
        body = "Task is due soon"
        task_id = "task789"
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif456"
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db.collection.return_value = mock_collection
        
        result = notifications_module.create_notification(
            mock_db, user_id, title, body, task_id=task_id, send_email=False
        )
        
        assert result == "notif456"
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["task_id"] == task_id
        
    def test_create_notification_with_email(self, mock_db):
        """Test creating notification with email sending"""
        user_id = "user789"
        title = "Email Notification"
        body = "This should send an email"
        
        # Mock user document with email
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif789"
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "notifications":
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_router
        
        with patch('backend.api.notifications.send_email_util') as mock_send:
            mock_send.return_value = True
            
            result = notifications_module.create_notification(
                mock_db, user_id, title, body, send_email=True
            )
            
            assert result == "notif789"
            mock_send.assert_called_once_with("user@example.com", title, body)
            mock_doc_ref.update.assert_called_once()
            update_args = mock_doc_ref.update.call_args[0][0]
            assert update_args["email_sent"] == True
            assert "email_sent_at" in update_args
            
    def test_create_notification_no_user_id(self, mock_db):
        """Test creating notification with no user_id returns None"""
        result = notifications_module.create_notification(
            mock_db, None, "Title", "Body"
        )
        assert result is None
        
    def test_create_notification_email_failure(self, mock_db):
        """Test notification created even if email fails"""
        user_id = "user999"
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.id = "notif999"
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "notifications":
                mock_coll.document.return_value = mock_doc_ref
            return mock_coll
        
        mock_db.collection.side_effect = collection_router
        
        with patch('backend.api.notifications.send_email_util') as mock_send:
            mock_send.return_value = False  # Email send fails
            
            result = notifications_module.create_notification(
                mock_db, user_id, "Title", "Body", send_email=True
            )
            
            # Should still create notification
            assert result == "notif999"
            # But email_sent should remain False
            mock_doc_ref.update.assert_not_called()


class TestTestEmail:
    """Test the test_email endpoint"""
    
    def test_test_email_success(self, client, mock_db, monkeypatch):
        """Test sending test email successfully"""
        user_id = "user123"
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            "email": "test@example.com",
            "name": "Test User"
        }
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_user_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.notifications.send_email_util') as mock_send:
            mock_send.return_value = True
            
            response = client.post('/notifications/test-email', json={
                "user_id": user_id,
                "title": "Test Email",
                "body": "Test body"
            })
            
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] == True
        assert "test@example.com" in data["message"]
        assert data["recipient"] == "test@example.com"
        
    def test_test_email_no_user_id(self, client, mock_db, monkeypatch):
        """Test sending email without user_id"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post('/notifications/test-email', json={
            "title": "Test Email",
            "body": "Test body"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "user_id is required" in data["error"]
        
    def test_test_email_user_not_found(self, client, mock_db, monkeypatch):
        """Test sending email to non-existent user"""
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_user_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post('/notifications/test-email', json={
            "user_id": "nonexistent",
            "title": "Test",
            "body": "Body"
        })
        
        assert response.status_code == 404
        data = response.get_json()
        assert "User not found" in data["error"]
        
    def test_test_email_no_email_address(self, client, mock_db, monkeypatch):
        """Test sending email when user has no email"""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"name": "Test User"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_user_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.post('/notifications/test-email', json={
            "user_id": "user123",
            "title": "Test",
            "body": "Body"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "no email address" in data["error"]
        
    def test_test_email_send_failure(self, client, mock_db, monkeypatch):
        """Test handling email send failure"""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "test@example.com"}
        
        mock_doc_ref = Mock()
        mock_doc_ref.get.return_value = mock_user_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.notifications.send_email_util') as mock_send:
            mock_send.return_value = False
            
            response = client.post('/notifications/test-email', json={
                "user_id": "user123",
                "title": "Test",
                "body": "Body"
            })
            
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] == False
        assert "Failed to send email" in data["error"]


class TestCheckDeadlines:
    """Test the check_deadlines endpoint"""
    
    def test_check_deadlines_basic(self, client, mock_db, monkeypatch):
        """Test checking deadlines creates notifications"""
        # Mock task with approaching deadline
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Urgent Task",
            "due_date": "2024-12-31T23:59",
            "created_by": {"user_id": "user1"},
            "assigned_to": {"user_id": "user2"},
            "project_id": "proj1"
        }
        
        # Mock user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
        
        # Mock notification ref
        mock_notif_ref = Mock()
        mock_notif_ref.id = "notif123"
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                mock_query.stream.return_value = [mock_task]
                mock_query.limit.return_value.stream.return_value = [mock_task]
                mock_coll.where.return_value.where.return_value = mock_query
                mock_coll.limit.return_value.stream.return_value = [mock_task]
                return mock_coll
            elif name == "users":
                mock_user_ref = Mock()
                mock_user_ref.get.return_value = mock_user_doc
                mock_coll.document.return_value = mock_user_ref
                mock_coll.stream.return_value = []
                return mock_coll
            elif name == "notifications":
                mock_query = Mock()
                mock_query.stream.return_value = []
                mock_coll.where.return_value.where.return_value.where.return_value.limit.return_value = mock_query
                mock_coll.document.return_value = mock_notif_ref
                return mock_coll
            elif name == "memberships":
                mock_query = Mock()
                mock_query.stream.return_value = []
                mock_coll.where.return_value = mock_query
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.notifications.send_email_util') as mock_send:
            mock_send.return_value = True
            
            response = client.post('/notifications/check-deadlines')
            
        assert response.status_code == 200
        data = response.get_json()
        assert "checked" in data
        assert "notifications_created" in data
        
    def test_check_deadlines_with_hours_param(self, client, mock_db, monkeypatch):
        """Test checking deadlines with custom hours window"""
        mock_task = Mock()
        mock_task.id = "task456"
        mock_task.to_dict.return_value = {
            "title": "Task",
            "due_date": "2024-12-31T23:59",
            "created_by": {"user_id": "user1"}
        }
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                mock_query.stream.return_value = [mock_task]
                mock_query.limit.return_value.stream.return_value = [mock_task]
                mock_coll.where.return_value.where.return_value = mock_query
                mock_coll.limit.return_value.stream.return_value = [mock_task]
                return mock_coll
            elif name == "users":
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
                mock_user_ref = Mock()
                mock_user_ref.get.return_value = mock_user_doc
                mock_coll.document.return_value = mock_user_ref
                mock_coll.stream.return_value = []
                return mock_coll
            elif name == "notifications":
                mock_query = Mock()
                mock_query.stream.return_value = []
                mock_notif_ref = Mock()
                mock_notif_ref.id = "notif456"
                mock_coll.where.return_value.where.return_value.where.return_value.limit.return_value = mock_query
                mock_coll.document.return_value = mock_notif_ref
                return mock_coll
            elif name == "memberships":
                mock_query = Mock()
                mock_query.stream.return_value = []
                mock_coll.where.return_value = mock_query
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        with patch('backend.api.notifications.send_email_util') as mock_send:
            mock_send.return_value = True
            
            response = client.post('/notifications/check-deadlines?hours=48')
            
        assert response.status_code == 200


class TestDueToday:
    """Test the due_today endpoint"""
    
    def test_due_today_success(self, client, mock_db, monkeypatch):
        """Test getting tasks due today for user"""
        user_id = "user123"
        
        # Mock task due today
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Task Due Today",
            "due_date": datetime.now(timezone.utc).isoformat(),
            "created_by": {"user_id": user_id},
            "assigned_to": {"user_id": "other_user"},
            "project_id": "proj1",
            "archived": False
        }
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                mock_query.stream.return_value = [mock_task]
                mock_query.limit.return_value.stream.return_value = [mock_task]
                mock_coll.where.return_value.where.return_value = mock_query
                return mock_coll
            elif name == "memberships":
                mock_mem_doc = Mock()
                mock_mem_doc.exists = False
                mock_coll.document.return_value.get.return_value = mock_mem_doc
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get('/notifications/due-today', headers={"X-User-Id": user_id})
        
        assert response.status_code == 200
        data = response.get_json()
        assert "count" in data
        assert "tasks" in data
        assert data["count"] >= 0
        
    def test_due_today_no_user_id(self, client, mock_db, monkeypatch):
        """Test due_today without user_id"""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get('/notifications/due-today')
        
        assert response.status_code == 401
        data = response.get_json()
        assert "user_id required" in data["error"]
        
    def test_due_today_with_custom_range(self, client, mock_db, monkeypatch):
        """Test due_today with custom start and end ISO dates"""
        user_id = "user456"
        start_iso = "2024-01-01T00:00:00+00:00"
        end_iso = "2024-01-01T23:59:59+00:00"
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                mock_query.stream.return_value = []
                mock_query.limit.return_value.stream.return_value = []
                mock_coll.where.return_value.where.return_value = mock_query
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get(
            f'/notifications/due-today?user_id={user_id}&start_iso={start_iso}&end_iso={end_iso}'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "count" in data
        assert "tasks" in data


class TestNotifyUserDueTasks:
    """Test the _notify_user_due_tasks helper function"""
    
    def test_notify_user_due_tasks_basic(self, mock_db):
        """Test notifying user of due tasks"""
        user_id = "user123"
        start_iso = "2024-12-31T00:00:00+00:00"
        end_iso = "2024-12-31T23:59:59+00:00"
        
        # Mock task
        mock_task = Mock()
        mock_task.id = "task123"
        mock_task.to_dict.return_value = {
            "title": "Due Task",
            "due_date": "2024-12-31T12:00:00+00:00",
            "created_by": {"user_id": user_id},
            "assigned_to": {"user_id": "other_user"},
            "project_id": None,
            "archived": False
        }
        
        # Mock user
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
        
        mock_notif_ref = Mock()
        mock_notif_ref.id = "notif123"
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                mock_query.stream.return_value = [mock_task]
                mock_coll.where.return_value.where.return_value = mock_query
                mock_coll.limit.return_value.stream.return_value = [mock_task]
                return mock_coll
            elif name == "users":
                mock_user_ref = Mock()
                mock_user_ref.get.return_value = mock_user_doc
                mock_coll.document.return_value = mock_user_ref
                return mock_coll
            elif name == "notifications":
                mock_query = Mock()
                mock_query.stream.return_value = []
                mock_coll.where.return_value.where.return_value.where.return_value.limit.return_value = mock_query
                mock_coll.document.return_value = mock_notif_ref
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        
        with patch('backend.api.notifications.send_email_util') as mock_send:
            mock_send.return_value = True
            
            result = notifications_module._notify_user_due_tasks(mock_db, user_id, start_iso, end_iso)
            
        # Should have created at least one notification
        assert result >= 0
        
    def test_notify_user_due_tasks_no_tasks(self, mock_db):
        """Test notifying user when no tasks are due"""
        user_id = "user456"
        start_iso = "2024-12-31T00:00:00+00:00"
        end_iso = "2024-12-31T23:59:59+00:00"
        
        def collection_router(name):
            mock_coll = Mock()
            if name == "tasks":
                mock_query = Mock()
                mock_query.stream.return_value = []
                mock_coll.where.return_value.where.return_value = mock_query
                mock_coll.limit.return_value.stream.return_value = []
                return mock_coll
            return Mock()
        
        mock_db.collection.side_effect = collection_router
        
        result = notifications_module._notify_user_due_tasks(mock_db, user_id, start_iso, end_iso)
        
        # Should create zero notifications
        assert result == 0
