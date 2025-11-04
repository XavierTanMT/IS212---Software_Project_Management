"""
Comprehensive tests to achieve 100% coverage for notifications.py
Tests notification creation, email sending, deadline checking, and all edge cases
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta


class TestNotificationCreation:
    """Tests for create_notification function"""
    
    def test_create_notification_basic(self, client, mock_db):
        """Test basic notification creation without email"""
        from backend.api.notifications import create_notification
        
        mock_ref = Mock()
        mock_ref.id = "notif123"
        mock_ref.set = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        result = create_notification(mock_db, "user123", "Test Title", "Test Body")
        
        assert result == "notif123"
        mock_ref.set.assert_called_once()
        call_args = mock_ref.set.call_args[0][0]
        assert call_args["user_id"] == "user123"
        assert call_args["title"] == "Test Title"
        assert call_args["body"] == "Test Body"
        assert call_args["read"] is False
    
    def test_create_notification_with_task_id(self, client, mock_db):
        """Test notification creation with task_id"""
        from backend.api.notifications import create_notification
        
        mock_ref = Mock()
        mock_ref.id = "notif123"
        mock_ref.set = Mock()
        mock_db.collection.return_value.document.return_value = mock_ref
        
        result = create_notification(mock_db, "user123", "Title", "Body", task_id="task123")
        
        call_args = mock_ref.set.call_args[0][0]
        assert call_args["task_id"] == "task123"
    
    def test_create_notification_empty_user_id(self, client, mock_db):
        """Test notification creation with empty user_id returns None"""
        from backend.api.notifications import create_notification
        
        result = create_notification(mock_db, "", "Title", "Body")
        assert result is None
    
    def test_create_notification_with_email_success(self, client, mock_db):
        """Test notification creation with email sending"""
        from backend.api.notifications import create_notification
        
        # Mock user doc
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
        
        # Mock notification ref
        mock_ref = Mock()
        mock_ref.id = "notif123"
        mock_ref.set = Mock()
        mock_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "notifications":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        
        assert result == "notif123"
        mock_ref.update.assert_called_once()
        update_args = mock_ref.update.call_args[0][0]
        assert update_args["email_sent"] is True
    
    def test_create_notification_with_email_failure(self, client, mock_db):
        """Test notification creation when email sending fails"""
        from backend.api.notifications import create_notification
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "user@example.com"}
        
        mock_ref = Mock()
        mock_ref.id = "notif123"
        mock_ref.set = Mock()
        mock_ref.update = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "notifications":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.notifications.send_email_util', return_value=False):
            result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        
        assert result == "notif123"
        # Update should not be called if email failed
        mock_ref.update.assert_not_called()
    
    def test_create_notification_user_not_found(self, client, mock_db):
        """Test notification creation when user doesn't exist"""
        from backend.api.notifications import create_notification
        
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        
        mock_ref = Mock()
        mock_ref.id = "notif123"
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "notifications":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        
        # Should still create notification even if user not found
        assert result == "notif123"
        mock_ref.set.assert_called_once()
    
    def test_create_notification_user_no_email(self, client, mock_db):
        """Test notification creation when user has no email"""
        from backend.api.notifications import create_notification
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"name": "User"}  # No email
        
        mock_ref = Mock()
        mock_ref.id = "notif123"
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.return_value = mock_user_doc
            elif name == "notifications":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.notifications.send_email_util') as mock_email:
            result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        
        assert result == "notif123"
        # Email should not be sent if no email address
        mock_email.assert_not_called()
    
    def test_create_notification_user_fetch_exception(self, client, mock_db):
        """Test notification creation when fetching user raises exception"""
        from backend.api.notifications import create_notification
        
        mock_ref = Mock()
        mock_ref.id = "notif123"
        mock_ref.set = Mock()
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "users":
                mock_coll.document.return_value.get.side_effect = Exception("DB error")
            elif name == "notifications":
                mock_coll.document.return_value = mock_ref
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        result = create_notification(mock_db, "user123", "Title", "Body", send_email=True)
        
        # Should still create notification despite exception
        assert result == "notif123"


class TestTestEmailEndpoint:
    """Tests for /api/notifications/test-email endpoint"""
    
    def test_test_email_success(self, client, mock_db):
        """Test successful email sending"""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "test@example.com"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            response = client.post("/api/notifications/test-email", json={
                "user_id": "user123",
                "title": "Test Subject",
                "body": "Test Body"
            })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "test@example.com" in data["message"]
    
    def test_test_email_missing_user_id(self, client, mock_db):
        """Test test-email without user_id"""
        response = client.post("/api/notifications/test-email", json={
            "title": "Test",
            "body": "Body"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "user_id is required" in data["error"]
    
    def test_test_email_user_not_found(self, client, mock_db):
        """Test test-email when user doesn't exist"""
        mock_user_doc = Mock()
        mock_user_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        response = client.post("/api/notifications/test-email", json={
            "user_id": "nonexistent"
        })
        
        assert response.status_code == 404
        data = response.get_json()
        assert "User not found" in data["error"]
    
    def test_test_email_no_email_address(self, client, mock_db):
        """Test test-email when user has no email"""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"name": "User"}  # No email
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        response = client.post("/api/notifications/test-email", json={
            "user_id": "user123"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "no email address" in data["error"]
    
    def test_test_email_send_failure(self, client, mock_db):
        """Test test-email when email sending fails"""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "test@example.com"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        with patch('backend.api.notifications.send_email_util', return_value=False):
            response = client.post("/api/notifications/test-email", json={
                "user_id": "user123"
            })
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to send email" in data["error"]
    
    def test_test_email_default_values(self, client, mock_db):
        """Test test-email with default title and body"""
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "test@example.com"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        with patch('backend.api.notifications.send_email_util', return_value=True) as mock_send:
            response = client.post("/api/notifications/test-email", json={
                "user_id": "user123"
            })
        
        assert response.status_code == 200
        # Check default values were used
        call_args = mock_send.call_args[0]
        assert "Test Email" in call_args[1]  # Default title
        assert "This is a test email" in call_args[2]  # Default body


class TestCheckDeadlinesEndpoint:
    """Tests for /api/notifications/check-deadlines endpoint"""
    
    def test_check_deadlines_basic(self, client, mock_db):
        """Test basic deadline checking"""
        # Mock task with upcoming deadline
        task = Mock()
        task.id = "task123"
        task.to_dict.return_value = {
            "title": "Urgent Task",
            "due_date": "2025-11-05T10:00:00+00:00",
            "created_by": {"user_id": "creator123"},
            "assigned_to": {"user_id": "assignee456"},
            "project_id": None
        }
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [task]
        mock_query.stream.return_value = [task]
        
        # Mock users collection
        mock_users_query = Mock()
        mock_users_query.stream.return_value = []
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                return mock_query
            elif name == "notifications":
                mock_notif_query = Mock()
                mock_notif_query.where.return_value = mock_notif_query
                mock_limit_mock = Mock()
                mock_limit_mock.stream.return_value = []
                mock_notif_query.limit.return_value = mock_limit_mock
                mock_coll.document.return_value = Mock(id="notif123", set=Mock())
                return mock_notif_query
            elif name == "users":
                mock_coll.stream.return_value = mock_users_query.stream()
                user_doc = Mock()
                user_doc.exists = True
                user_doc.to_dict.return_value = {"email": "user@example.com"}
                mock_coll.document.return_value.get.return_value = user_doc
                return mock_coll
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            response = client.post("/api/notifications/check-deadlines?hours=24")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "checked" in data
        assert "notifications_created" in data
    
    def test_check_deadlines_custom_window(self, client, mock_db):
        """Test deadline checking with custom start/end ISO"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = []
        mock_query.stream.return_value = []
        
        mock_users_query = Mock()
        mock_users_query.stream.return_value = []
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                return mock_query
            elif name == "users":
                mock_coll.stream.return_value = []
                return mock_coll
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.post("/api/notifications/check-deadlines?start_iso=2025-11-01T00:00:00Z&end_iso=2025-11-02T00:00:00Z")
        
        assert response.status_code == 200
    
    def test_check_deadlines_resend_existing(self, client, mock_db):
        """Test resending emails for existing notifications"""
        task = Mock()
        task.id = "task123"
        task.to_dict.return_value = {
            "title": "Task",
            "due_date": "2025-11-05T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
            "assigned_to": None,
            "project_id": None
        }
        
        # Mock existing notification
        existing_notif = Mock()
        existing_notif.reference = Mock()
        existing_notif.reference.update = Mock()
        existing_notif.to_dict.return_value = {"email_sent": False}
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [task]
        mock_query.stream.return_value = [task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                return mock_query
            elif name == "notifications":
                mock_notif_query = Mock()
                mock_notif_query.where.return_value = mock_notif_query
                mock_limit_mock = Mock()
                mock_limit_mock.stream.return_value = [existing_notif]
                mock_notif_query.limit.return_value = mock_limit_mock
                return mock_notif_query
            elif name == "users":
                mock_coll.stream.return_value = []
                user_doc = Mock()
                user_doc.exists = True
                user_doc.to_dict.return_value = {"email": "user@example.com"}
                mock_coll.document.return_value.get.return_value = user_doc
                return mock_coll
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            response = client.post("/api/notifications/check-deadlines?resend_existing=true")
        
        assert response.status_code == 200
        # Verify update was called to mark email as sent
        existing_notif.reference.update.assert_called_once()
    
    def test_check_deadlines_with_project_members(self, client, mock_db):
        """Test deadline checking includes project members"""
        task = Mock()
        task.id = "task123"
        task.to_dict.return_value = {
            "title": "Project Task",
            "due_date": "2025-11-05T10:00:00+00:00",
            "created_by": None,
            "assigned_to": None,
            "project_id": "proj123"
        }
        
        # Mock membership
        member = Mock()
        member.to_dict.return_value = {"user_id": "member123"}
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [task]
        mock_query.stream.return_value = [task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                return mock_query
            elif name == "memberships":
                mock_mem_query = Mock()
                mock_mem_query.where.return_value = mock_mem_query
                mock_mem_query.stream.return_value = [member]
                return mock_mem_query
            elif name == "notifications":
                mock_notif_query = Mock()
                mock_notif_query.where.return_value = mock_notif_query
                mock_limit_mock = Mock()
                mock_limit_mock.stream.return_value = []
                mock_notif_query.limit.return_value = mock_limit_mock
                mock_coll.document.return_value = Mock(id="notif123", set=Mock())
                return mock_notif_query
            elif name == "users":
                mock_coll.stream.return_value = []
                user_doc = Mock()
                user_doc.exists = True
                user_doc.to_dict.return_value = {"email": "member@example.com"}
                mock_coll.document.return_value.get.return_value = user_doc
                return mock_coll
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        with patch('backend.api.notifications.send_email_util', return_value=True):
            response = client.post("/api/notifications/check-deadlines")
        
        assert response.status_code == 200


class TestDueTodayEndpoint:
    """Tests for /api/notifications/due-today endpoint"""
    
    def test_due_today_no_user_id(self, client, mock_db):
        """Test due-today without user_id"""
        response = client.get("/api/notifications/due-today")
        
        assert response.status_code == 401
        data = response.get_json()
        assert "user_id required" in data["error"]
    
    def test_due_today_as_creator(self, client, mock_db):
        """Test due-today returns tasks where user is creator"""
        task = Mock()
        task.id = "task123"
        task.to_dict.return_value = {
            "title": "My Task",
            "due_date": "2025-11-04T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
            "assigned_to": None,
            "project_id": None,
            "archived": False
        }
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [task]
        mock_query.stream.return_value = [task]
        
        mock_db.collection.return_value = mock_query
        
        response = client.get("/api/notifications/due-today?user_id=user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == "task123"
    
    def test_due_today_as_assignee(self, client, mock_db):
        """Test due-today returns tasks where user is assignee"""
        task = Mock()
        task.id = "task123"
        task.to_dict.return_value = {
            "title": "Assigned Task",
            "due_date": "2025-11-04T10:00:00+00:00",
            "created_by": None,
            "assigned_to": {"user_id": "user123"},
            "project_id": None,
            "archived": False
        }
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [task]
        mock_query.stream.return_value = [task]
        
        mock_db.collection.return_value = mock_query
        
        response = client.get("/api/notifications/due-today?user_id=user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
    
    def test_due_today_as_project_member(self, client, mock_db):
        """Test due-today returns tasks for project members"""
        task = Mock()
        task.id = "task123"
        task.to_dict.return_value = {
            "title": "Project Task",
            "due_date": "2025-11-04T10:00:00+00:00",
            "created_by": None,
            "assigned_to": None,
            "project_id": "proj123",
            "archived": False
        }
        
        # Mock membership exists
        mock_membership = Mock()
        mock_membership.exists = True
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [task]
        mock_query.stream.return_value = [task]
        
        def collection_side_effect(name):
            mock_coll = Mock()
            if name == "tasks":
                return mock_query
            elif name == "memberships":
                mock_coll.document.return_value.get.return_value = mock_membership
                return mock_coll
            return mock_coll
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        
        response = client.get("/api/notifications/due-today?user_id=user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
    
    def test_due_today_excludes_archived(self, client, mock_db):
        """Test due-today excludes archived tasks"""
        task = Mock()
        task.id = "task123"
        task.to_dict.return_value = {
            "title": "Archived Task",
            "due_date": "2025-11-04T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
            "assigned_to": None,
            "project_id": None,
            "archived": True
        }
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [task]
        mock_query.stream.return_value = [task]
        
        mock_db.collection.return_value = mock_query
        
        response = client.get("/api/notifications/due-today?user_id=user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 0  # Archived task excluded
    
    def test_due_today_not_involved(self, client, mock_db):
        """Test due-today excludes tasks user is not involved in"""
        task = Mock()
        task.id = "task123"
        task.to_dict.return_value = {
            "title": "Other User Task",
            "due_date": "2025-11-04T10:00:00+00:00",
            "created_by": {"user_id": "other_user"},
            "assigned_to": {"user_id": "another_user"},
            "project_id": None,
            "archived": False
        }
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [task]
        mock_query.stream.return_value = [task]
        
        mock_db.collection.return_value = mock_query
        
        response = client.get("/api/notifications/due-today?user_id=user123")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 0
    
    def test_due_today_custom_date_range(self, client, mock_db):
        """Test due-today with custom start/end ISO"""
        task = Mock()
        task.id = "task123"
        task.to_dict.return_value = {
            "title": "Task",
            "due_date": "2025-11-05T10:00:00+00:00",
            "created_by": {"user_id": "user123"},
            "assigned_to": None,
            "project_id": None,
            "archived": False
        }
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [task]
        mock_query.stream.return_value = [task]
        
        mock_db.collection.return_value = mock_query
        
        response = client.get("/api/notifications/due-today?user_id=user123&start_iso=2025-11-05T00:00:00Z&end_iso=2025-11-06T00:00:00Z")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
