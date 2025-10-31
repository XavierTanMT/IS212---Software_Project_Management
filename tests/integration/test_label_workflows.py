"""Integration tests for label workflows using real Firebase."""
import pytest
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter


class TestLabelOperations:
    """Test basic label CRUD operations with real Firebase."""
    
    def test_create_and_list_labels(self, db, test_collection_prefix, cleanup_collections):
        """Test creating labels and listing them."""
        collection_name = f"{test_collection_prefix}_labels"
        cleanup_collections.append(collection_name)
        
        # Create multiple labels
        labels_data = [
            {"label_id": f"label_bug_{datetime.now(timezone.utc).timestamp()}", "name": "Bug", "color": "#FF0000"},
            {"label_id": f"label_feature_{datetime.now(timezone.utc).timestamp()}", "name": "Feature", "color": "#00FF00"},
            {"label_id": f"label_urgent_{datetime.now(timezone.utc).timestamp()}", "name": "Urgent", "color": "#FFA500"}
        ]
        
        label_ids = []
        for label_data in labels_data:
            label_id = label_data["label_id"]
            db.collection(collection_name).document(label_id).set(label_data)
            label_ids.append(label_id)
        
        # List all labels
        labels = [doc.to_dict() for doc in db.collection(collection_name).stream()]
        
        assert len(labels) >= 3
        label_names = [l["name"] for l in labels]
        assert "Bug" in label_names
        assert "Feature" in label_names
        assert "Urgent" in label_names
        
        # Cleanup
        for label_id in label_ids:
            db.collection(collection_name).document(label_id).delete()
    
    
    def test_update_label(self, db, test_collection_prefix, cleanup_collections):
        """Test updating a label's properties."""
        collection_name = f"{test_collection_prefix}_labels"
        cleanup_collections.append(collection_name)
        
        label_id = f"label_{datetime.now(timezone.utc).timestamp()}"
        label_data = {
            "label_id": label_id,
            "name": "Bug",
            "color": "#FF0000"
        }
        
        # Create label
        db.collection(collection_name).document(label_id).set(label_data)
        
        # Update label
        db.collection(collection_name).document(label_id).update({
            "name": "Critical Bug",
            "color": "#CC0000"
        })
        
        # Verify update
        doc = db.collection(collection_name).document(label_id).get()
        updated_data = doc.to_dict()
        
        assert updated_data["name"] == "Critical Bug"
        assert updated_data["color"] == "#CC0000"
        
        # Cleanup
        db.collection(collection_name).document(label_id).delete()
    
    
    def test_delete_label(self, db, test_collection_prefix, cleanup_collections):
        """Test deleting a label."""
        collection_name = f"{test_collection_prefix}_labels"
        cleanup_collections.append(collection_name)
        
        label_id = f"label_{datetime.now(timezone.utc).timestamp()}"
        label_data = {
            "label_id": label_id,
            "name": "Deprecated",
            "color": "#CCCCCC"
        }
        
        # Create label
        db.collection(collection_name).document(label_id).set(label_data)
        
        # Verify creation
        doc = db.collection(collection_name).document(label_id).get()
        assert doc.exists
        
        # Delete label
        db.collection(collection_name).document(label_id).delete()
        
        # Verify deletion
        doc = db.collection(collection_name).document(label_id).get()
        assert not doc.exists


class TestTaskLabelAssignment:
    """Test assigning and unassigning labels to tasks."""
    
    def test_assign_labels_to_task(self, db, test_collection_prefix, cleanup_collections):
        """Test assigning multiple labels to a task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        labels_collection = f"{test_collection_prefix}_labels"
        task_labels_collection = f"{test_collection_prefix}_task_labels"
        cleanup_collections.extend([tasks_collection, labels_collection, task_labels_collection])
        
        # Create task
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Task with Labels",
            "status": "To Do",
            "labels": []
        })
        
        # Create labels
        label_ids = []
        for i, name in enumerate(["Bug", "Urgent", "Backend"]):
            label_id = f"label_{name.lower()}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(labels_collection).document(label_id).set({
                "label_id": label_id,
                "name": name,
                "color": f"#FF{i*3}000"
            })
            label_ids.append(label_id)
        
        # Assign labels to task (simulate task_labels join table)
        task_label_doc_id = f"{task_id}_{label_ids[0]}"
        db.collection(task_labels_collection).document(task_label_doc_id).set({
            "task_id": task_id,
            "label_id": label_ids[0]
        })
        
        # Update task with label IDs
        db.collection(tasks_collection).document(task_id).update({
            "labels": label_ids[:2]  # Assign first 2 labels
        })
        
        # Verify task has labels
        task_doc = db.collection(tasks_collection).document(task_id).get()
        task_data = task_doc.to_dict()
        
        assert len(task_data["labels"]) == 2
        assert label_ids[0] in task_data["labels"]
        assert label_ids[1] in task_data["labels"]
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
        db.collection(task_labels_collection).document(task_label_doc_id).delete()
        for label_id in label_ids:
            db.collection(labels_collection).document(label_id).delete()
    
    
    def test_unassign_label_from_task(self, db, test_collection_prefix, cleanup_collections):
        """Test removing a label from a task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        labels_collection = f"{test_collection_prefix}_labels"
        cleanup_collections.extend([tasks_collection, labels_collection])
        
        # Create label
        label_id = f"label_{datetime.now(timezone.utc).timestamp()}"
        db.collection(labels_collection).document(label_id).set({
            "label_id": label_id,
            "name": "Bug",
            "color": "#FF0000"
        })
        
        # Create task with label
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Task with Label",
            "status": "To Do",
            "labels": [label_id]
        })
        
        # Verify task has label
        task_doc = db.collection(tasks_collection).document(task_id).get()
        assert label_id in task_doc.to_dict()["labels"]
        
        # Remove label from task
        db.collection(tasks_collection).document(task_id).update({
            "labels": []
        })
        
        # Verify label removed
        task_doc = db.collection(tasks_collection).document(task_id).get()
        assert task_doc.to_dict()["labels"] == []
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
        db.collection(labels_collection).document(label_id).delete()
    
    
    def test_query_tasks_by_label(self, db, test_collection_prefix, cleanup_collections):
        """Test querying tasks that have a specific label."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        labels_collection = f"{test_collection_prefix}_labels"
        cleanup_collections.extend([tasks_collection, labels_collection])
        
        # Create label
        label_id = f"label_{datetime.now(timezone.utc).timestamp()}"
        db.collection(labels_collection).document(label_id).set({
            "label_id": label_id,
            "name": "Urgent",
            "color": "#FF0000"
        })
        
        # Create tasks - some with label, some without
        task_ids_with_label = []
        task_ids_without_label = []
        
        for i in range(3):
            task_id = f"task_with_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(tasks_collection).document(task_id).set({
                "task_id": task_id,
                "title": f"Urgent Task {i}",
                "status": "To Do",
                "labels": [label_id]
            })
            task_ids_with_label.append(task_id)
        
        for i in range(2):
            task_id = f"task_without_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(tasks_collection).document(task_id).set({
                "task_id": task_id,
                "title": f"Normal Task {i}",
                "status": "To Do",
                "labels": []
            })
            task_ids_without_label.append(task_id)
        
        # Query tasks with the label using array-contains
        query = db.collection(tasks_collection).where(filter=FieldFilter("labels", "array_contains", label_id))
        tasks_with_label = [doc.to_dict() for doc in query.stream()]
        
        # Verify results
        assert len(tasks_with_label) >= 3
        retrieved_task_ids = [t["task_id"] for t in tasks_with_label]
        for task_id in task_ids_with_label:
            assert task_id in retrieved_task_ids
        
        # Cleanup
        for task_id in task_ids_with_label + task_ids_without_label:
            db.collection(tasks_collection).document(task_id).delete()
        db.collection(labels_collection).document(label_id).delete()


class TestLabelEdgeCases:
    """Test edge cases and complex label scenarios."""
    
    def test_task_with_multiple_labels(self, db, test_collection_prefix, cleanup_collections):
        """Test a task with multiple labels assigned."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        labels_collection = f"{test_collection_prefix}_labels"
        cleanup_collections.extend([tasks_collection, labels_collection])
        
        # Create multiple labels
        label_data = [
            ("Bug", "#FF0000"),
            ("Urgent", "#FFA500"),
            ("Backend", "#0000FF"),
            ("Security", "#FF00FF")
        ]
        
        label_ids = []
        for name, color in label_data:
            label_id = f"label_{name.lower()}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(labels_collection).document(label_id).set({
                "label_id": label_id,
                "name": name,
                "color": color
            })
            label_ids.append(label_id)
        
        # Create task with all labels
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Complex Task",
            "status": "In Progress",
            "labels": label_ids
        })
        
        # Verify all labels assigned
        task_doc = db.collection(tasks_collection).document(task_id).get()
        task_labels = task_doc.to_dict()["labels"]
        
        assert len(task_labels) == 4
        for label_id in label_ids:
            assert label_id in task_labels
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
        for label_id in label_ids:
            db.collection(labels_collection).document(label_id).delete()
    
    
    def test_label_color_formats(self, db, test_collection_prefix, cleanup_collections):
        """Test labels with various color format specifications."""
        collection_name = f"{test_collection_prefix}_labels"
        cleanup_collections.append(collection_name)
        
        # Test different color formats
        color_tests = [
            ("#FF0000", "6-digit hex"),
            ("#F00", "3-digit hex"),
            ("#AABBCCDD", "8-digit hex with alpha"),
        ]
        
        label_ids = []
        for color, description in color_tests:
            label_id = f"label_{datetime.now(timezone.utc).timestamp()}_{len(label_ids)}"
            db.collection(collection_name).document(label_id).set({
                "label_id": label_id,
                "name": f"Color Test {description}",
                "color": color
            })
            label_ids.append(label_id)
        
        # Verify all labels created successfully
        for label_id in label_ids:
            doc = db.collection(collection_name).document(label_id).get()
            assert doc.exists
            assert "color" in doc.to_dict()
        
        # Cleanup
        for label_id in label_ids:
            db.collection(collection_name).document(label_id).delete()
