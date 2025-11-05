import sys
from unittest.mock import Mock
import pytest

fake_firestore = sys.modules.get("firebase_admin.firestore")
from backend.api import tags_bp as labels_bp
from backend.api import tags as labels_module


class TestListTags:
    def test_list_tags_success(self, client, mock_db, monkeypatch):
        """Test successfully listing tags from multiple tasks."""
        mock_task1 = Mock()
        mock_task1.id = "task1"
        mock_task1.to_dict = Mock(return_value={"title": "Task 1", "tags": ["bug", "urgent"]})
        
        mock_task2 = Mock()
        mock_task2.id = "task2"
        mock_task2.to_dict = Mock(return_value={"title": "Task 2", "tags": ["feature", "urgent"]})
        
        mock_collection = Mock()
        mock_collection.stream = Mock(return_value=[mock_task1, mock_task2])
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/tags")
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert "bug" in data
        assert "feature" in data
        assert "urgent" in data
        assert data == sorted(data)
    
    def test_list_tags_no_tasks(self, client, mock_db, monkeypatch):
        """Test listing tags when there are no tasks."""
        mock_collection = Mock()
        mock_collection.stream = Mock(return_value=[])
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/tags")
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0
