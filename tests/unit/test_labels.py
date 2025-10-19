import sys
import os
from unittest.mock import Mock, patch
import pytest

# Get fake_firestore from sys.modules (set up by conftest.py)
fake_firestore = sys.modules.get("firebase_admin.firestore")

from flask import Flask
from backend.api import labels_bp
from backend.api import labels as labels_module


@pytest.fixture(autouse=True)
def mock_firestore_array_ops():
    """Automatically mock ArrayUnion and ArrayRemove for all tests in this file."""
    # Import labels module to get its firestore reference
    import backend.api.labels as labels
    
    # Create mocks that just return their input
    array_union_mock = Mock(side_effect=lambda x: x)
    array_remove_mock = Mock(side_effect=lambda x: x)
    
    # Directly set them on the firestore object that labels.py uses
    labels.firestore.ArrayUnion = array_union_mock
    labels.firestore.ArrayRemove = array_remove_mock
    
    yield {"ArrayUnion": array_union_mock, "ArrayRemove": array_remove_mock}
    
    # Clean up after test
    if hasattr(labels.firestore, "ArrayUnion"):
        delattr(labels.firestore, "ArrayUnion")
    if hasattr(labels.firestore, "ArrayRemove"):
        delattr(labels.firestore, "ArrayRemove")


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask('test_labels_app')
    app.config['TESTING'] = True
    # Use try-except to handle blueprint already registered
    try:
        app.register_blueprint(labels_bp)
    except AssertionError:
        # Blueprint already registered, that's okay
        pass
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestCreateLabel:
    """Test the create_label endpoint."""
    
    def test_create_label_success(self, client, mock_db, monkeypatch):
        """Test successfully creating a label with name and color."""
        # Mock Firestore
        mock_doc_ref = Mock()
        mock_doc_ref.id = "label123"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        # Test data
        payload = {
            "name": "Bug",
            "color": "#FF0000"
        }
        
        response = client.post(
            "/api/labels",
            json=payload,
            content_type="application/json"
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.get_json()
        assert data["label_id"] == "label123"
        assert data["name"] == "Bug"
        assert data["color"] == "#FF0000"
        
        # Verify Firestore was called correctly
        mock_db.collection.assert_called_once_with("labels")
        mock_collection.document.assert_called_once()
        mock_doc_ref.set.assert_called_once()
        
        # Verify the document structure
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["name"] == "Bug"
        assert call_args["color"] == "#FF0000"
    
    def test_create_label_without_color(self, client, mock_db, monkeypatch):
        """Test creating a label without color (should default to None)."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "label456"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "Feature"
        }
        
        response = client.post("/api/labels", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Feature"
        assert data["color"] is None
        
        # Verify stored document
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["color"] is None
    
    def test_create_label_empty_color(self, client, mock_db, monkeypatch):
        """Test creating a label with empty color string (should default to None)."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "label789"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "Documentation",
            "color": ""
        }
        
        response = client.post("/api/labels", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["color"] is None
    
    def test_create_label_missing_name(self, client, mock_db, monkeypatch):
        """Test creating a label without name returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "color": "#00FF00"
        }
        
        response = client.post("/api/labels", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "name is required" in data["error"]
    
    def test_create_label_empty_name(self, client, mock_db, monkeypatch):
        """Test creating a label with empty name returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "",
            "color": "#00FF00"
        }
        
        response = client.post("/api/labels", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "name is required" in data["error"]
    
    def test_create_label_whitespace_only_name(self, client, mock_db, monkeypatch):
        """Test creating a label with whitespace-only name returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "   ",
            "color": "#00FF00"
        }
        
        response = client.post("/api/labels", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_create_label_trims_whitespace(self, client, mock_db, monkeypatch):
        """Test that whitespace is trimmed from name and color."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "label_trim"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "  Enhancement  ",
            "color": "  #0000FF  "
        }
        
        response = client.post("/api/labels", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Enhancement"
        assert data["color"] == "#0000FF"
    
    def test_create_label_no_payload(self, client, mock_db, monkeypatch):
        """Test creating a label with no JSON payload - empty request body."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))

        # Send empty JSON object (get_json(force=True) or {} makes this {})
        response = client.post("/api/labels", json={})

        assert response.status_code == 400
        data = response.get_json()
        assert data is not None
        assert "error" in data
        assert data["error"] == "name is required"
class TestListLabels:
    """Test the list_labels endpoint."""
    
    def test_list_labels_success(self, client, mock_db, monkeypatch):
        """Test successfully listing labels."""
        # Mock label documents
        mock_label1 = Mock()
        mock_label1.id = "label1"
        mock_label1.to_dict = Mock(return_value={
            "name": "Bug",
            "color": "#FF0000"
        })
        
        mock_label2 = Mock()
        mock_label2.id = "label2"
        mock_label2.to_dict = Mock(return_value={
            "name": "Feature",
            "color": "#00FF00"
        })
        
        mock_collection = Mock()
        mock_collection.stream = Mock(return_value=[mock_label1, mock_label2])
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/labels")
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify response
        assert len(data) == 2
        assert data[0]["label_id"] == "label1"
        assert data[0]["name"] == "Bug"
        assert data[0]["color"] == "#FF0000"
        assert data[1]["label_id"] == "label2"
        assert data[1]["name"] == "Feature"
        assert data[1]["color"] == "#00FF00"
        
        # Verify Firestore query
        mock_db.collection.assert_called_once_with("labels")
        mock_collection.stream.assert_called_once()
    
    def test_list_labels_empty(self, client, mock_db, monkeypatch):
        """Test listing labels when no labels exist."""
        mock_collection = Mock()
        mock_collection.stream = Mock(return_value=[])
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/labels")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []
    
    def test_list_labels_single_label(self, client, mock_db, monkeypatch):
        """Test listing labels with a single label."""
        mock_label = Mock()
        mock_label.id = "only_label"
        mock_label.to_dict = Mock(return_value={
            "name": "Priority",
            "color": None
        })
        
        mock_collection = Mock()
        mock_collection.stream = Mock(return_value=[mock_label])
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        response = client.get("/api/labels")
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["label_id"] == "only_label"
        assert data[0]["name"] == "Priority"
        assert data[0]["color"] is None


class TestAssignLabel:
    """Test the assign_label endpoint."""
    
    def test_assign_label_success(self, client, mock_db, monkeypatch):
        """Test successfully assigning a label to a task."""
        # Mock Firestore
        mock_task_labels_doc = Mock()
        mock_task_labels_doc.set = Mock()
        
        mock_task_ref = Mock()
        mock_task_ref.set = Mock()
        
        def collection_side_effect(name):
            if name == "task_labels":
                mock_collection = Mock()
                mock_collection.document = Mock(return_value=mock_task_labels_doc)
                return mock_collection
            elif name == "tasks":
                mock_collection = Mock()
                mock_collection.document = Mock(return_value=mock_task_ref)
                return mock_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task123",
            "label_id": "label_abc"
        }
        
        response = client.post("/api/labels/assign", json=payload)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        
        # Verify task_labels document was created
        mock_task_labels_doc.set.assert_called_once_with({
            "task_id": "task123",
            "label_id": "label_abc"
        })
        
        # Verify task was updated with ArrayUnion
        mock_task_ref.set.assert_called_once()
        call_args = mock_task_ref.set.call_args
        assert "merge" in call_args[1]
        assert call_args[1]["merge"] is True
    
    def test_assign_label_missing_task_id(self, client, mock_db, monkeypatch):
        """Test assigning a label without task_id returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "label_id": "label_abc"
        }
        
        response = client.post("/api/labels/assign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "task_id and label_id are required" in data["error"]
    
    def test_assign_label_missing_label_id(self, client, mock_db, monkeypatch):
        """Test assigning a label without label_id returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task123"
        }
        
        response = client.post("/api/labels/assign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "task_id and label_id are required" in data["error"]
    
    def test_assign_label_empty_task_id(self, client, mock_db, monkeypatch):
        """Test assigning a label with empty task_id returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "",
            "label_id": "label_abc"
        }
        
        response = client.post("/api/labels/assign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_assign_label_empty_label_id(self, client, mock_db, monkeypatch):
        """Test assigning a label with empty label_id returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task123",
            "label_id": ""
        }
        
        response = client.post("/api/labels/assign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_assign_label_whitespace_ids(self, client, mock_db, monkeypatch):
        """Test assigning a label with whitespace-only IDs returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "   ",
            "label_id": "   "
        }
        
        response = client.post("/api/labels/assign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_assign_label_trims_whitespace(self, client, mock_db, monkeypatch):
        """Test that whitespace is trimmed from task_id and label_id."""
        mock_task_labels_doc = Mock()
        mock_task_labels_doc.set = Mock()
        
        mock_task_ref = Mock()
        mock_task_ref.set = Mock()
        
        def collection_side_effect(name):
            if name == "task_labels":
                mock_collection = Mock()
                mock_collection.document = Mock(return_value=mock_task_labels_doc)
                return mock_collection
            elif name == "tasks":
                mock_collection = Mock()
                mock_collection.document = Mock(return_value=mock_task_ref)
                return mock_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "  task999  ",
            "label_id": "  label_xyz  "
        }
        
        response = client.post("/api/labels/assign", json=payload)
        
        assert response.status_code == 200
        
        # Verify trimmed IDs were used
        call_args = mock_task_labels_doc.set.call_args[0][0]
        assert call_args["task_id"] == "task999"
        assert call_args["label_id"] == "label_xyz"


class TestUnassignLabel:
    """Test the unassign_label endpoint."""
    
    def test_unassign_label_success(self, client, mock_db, monkeypatch):
        """Test successfully unassigning a label from a task."""
        # Mock Firestore
        mock_task_labels_doc = Mock()
        mock_task_labels_doc.delete = Mock()
        
        mock_task_ref = Mock()
        mock_task_ref.set = Mock()
        
        def collection_side_effect(name):
            if name == "task_labels":
                mock_collection = Mock()
                mock_collection.document = Mock(return_value=mock_task_labels_doc)
                return mock_collection
            elif name == "tasks":
                mock_collection = Mock()
                mock_collection.document = Mock(return_value=mock_task_ref)
                return mock_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task456",
            "label_id": "label_def"
        }
        
        response = client.post("/api/labels/unassign", json=payload)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        
        # Verify task_labels document was deleted
        mock_task_labels_doc.delete.assert_called_once()
        
        # Verify task was updated with ArrayRemove
        mock_task_ref.set.assert_called_once()
        call_args = mock_task_ref.set.call_args
        assert "merge" in call_args[1]
        assert call_args[1]["merge"] is True
    
    def test_unassign_label_missing_task_id(self, client, mock_db, monkeypatch):
        """Test unassigning a label without task_id returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "label_id": "label_def"
        }
        
        response = client.post("/api/labels/unassign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "task_id and label_id are required" in data["error"]
    
    def test_unassign_label_missing_label_id(self, client, mock_db, monkeypatch):
        """Test unassigning a label without label_id returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task456"
        }
        
        response = client.post("/api/labels/unassign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "task_id and label_id are required" in data["error"]
    
    def test_unassign_label_empty_task_id(self, client, mock_db, monkeypatch):
        """Test unassigning a label with empty task_id returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "",
            "label_id": "label_def"
        }
        
        response = client.post("/api/labels/unassign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_unassign_label_empty_label_id(self, client, mock_db, monkeypatch):
        """Test unassigning a label with empty label_id returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "task456",
            "label_id": ""
        }
        
        response = client.post("/api/labels/unassign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_unassign_label_whitespace_ids(self, client, mock_db, monkeypatch):
        """Test unassigning a label with whitespace-only IDs returns error."""
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "   ",
            "label_id": "   "
        }
        
        response = client.post("/api/labels/unassign", json=payload)
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_unassign_label_trims_whitespace(self, client, mock_db, monkeypatch):
        """Test that whitespace is trimmed from task_id and label_id."""
        # Mock ArrayRemove
        mock_task_labels_doc = Mock()
        mock_task_labels_doc.delete = Mock()
        
        mock_task_ref = Mock()
        mock_task_ref.set = Mock()
        
        def collection_side_effect(name):
            if name == "task_labels":
                mock_collection = Mock()
                mock_collection.document = Mock(return_value=mock_task_labels_doc)
                return mock_collection
            elif name == "tasks":
                mock_collection = Mock()
                mock_collection.document = Mock(return_value=mock_task_ref)
                return mock_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "  task888  ",
            "label_id": "  label_ghi  "
        }
        
        response = client.post("/api/labels/unassign", json=payload)
        
        assert response.status_code == 200


class TestBlueprintRegistration:
    """Test that the blueprint is properly configured."""
    
    def test_blueprint_url_prefix(self):
        """Test that the blueprint has the correct URL prefix."""
        assert labels_bp.url_prefix == "/api/labels"
    
    def test_blueprint_name(self):
        """Test that the blueprint has the correct name."""
        assert labels_bp.name == "labels"


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_create_label_with_special_characters(self, client, mock_db, monkeypatch):
        """Test creating a label with special characters in name."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "label_special"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "High Priority! 🔥",
            "color": "red"
        }
        
        response = client.post("/api/labels", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "High Priority! 🔥"
    
    def test_create_label_with_css_color_name(self, client, mock_db, monkeypatch):
        """Test creating a label with CSS color name instead of hex."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "label_css"
        mock_doc_ref.set = Mock()
        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_db.collection = Mock(return_value=mock_collection)
        
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "name": "Info",
            "color": "blue"
        }
        
        response = client.post("/api/labels", json=payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["color"] == "blue"
    
    def test_assign_label_document_naming_convention(self, client, mock_db, monkeypatch):
        """Test that task_labels document uses correct naming convention."""
        mock_task_labels_collection = Mock()
        mock_task_labels_doc = Mock()
        mock_task_labels_doc.set = Mock()
        mock_task_labels_collection.document = Mock(return_value=mock_task_labels_doc)
        
        mock_task_collection = Mock()
        mock_task_ref = Mock()
        mock_task_ref.set = Mock()
        mock_task_collection.document = Mock(return_value=mock_task_ref)
        
        def collection_side_effect(name):
            if name == "task_labels":
                return mock_task_labels_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "tsk",
            "label_id": "lbl"
        }
        
        response = client.post("/api/labels/assign", json=payload)
        
        assert response.status_code == 200
        
        # Verify the document ID format: task_id_label_id
        mock_task_labels_collection.document.assert_called_once_with("tsk_lbl")
    
    def test_unassign_label_document_naming_convention(self, client, mock_db, monkeypatch):
        """Test that unassign uses correct document naming convention."""
        mock_task_labels_collection = Mock()
        mock_task_labels_doc = Mock()
        mock_task_labels_doc.delete = Mock()
        mock_task_labels_collection.document = Mock(return_value=mock_task_labels_doc)
        
        mock_task_collection = Mock()
        mock_task_ref = Mock()
        mock_task_ref.set = Mock()
        mock_task_collection.document = Mock(return_value=mock_task_ref)
        
        def collection_side_effect(name):
            if name == "task_labels":
                return mock_task_labels_collection
            elif name == "tasks":
                return mock_task_collection
            return Mock()
        
        mock_db.collection = Mock(side_effect=collection_side_effect)
        monkeypatch.setattr(fake_firestore, "client", Mock(return_value=mock_db))
        
        payload = {
            "task_id": "abc",
            "label_id": "xyz"
        }
        
        response = client.post("/api/labels/unassign", json=payload)
        
        assert response.status_code == 200
        
        # Verify the document ID format: task_id_label_id
        mock_task_labels_collection.document.assert_called_once_with("abc_xyz")
