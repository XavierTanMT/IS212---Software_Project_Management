"""Integration tests for task workflows using real Firebase."""
import pytest
import json
from datetime import datetime, timezone, timedelta
from google.cloud.firestore_v1.base_query import FieldFilter


class TestTaskOperations:
    """Test basic task CRUD operations with real Firebase."""
    
    def test_create_task_in_firestore(self, db, test_collection_prefix, cleanup_collections):
        """Test creating a task directly in Firestore."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        task_id = f"integration_task_{datetime.now(timezone.utc).timestamp()}"
        task_data = {
            "task_id": task_id,
            "title": "Integration Test Task",
            "description": "A task for integration testing",
            "status": "To Do",
            "priority": 5,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }
        
        # Create task
        db.collection(collection_name).document(task_id).set(task_data)
        
        # Verify creation
        doc = db.collection(collection_name).document(task_id).get()
        assert doc.exists
        assert doc.to_dict()["title"] == task_data["title"]
        assert doc.to_dict()["status"] == "To Do"
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
    
    
    def test_update_task_status(self, db, test_task):
        """Test updating task status."""
        collection = test_task["collection"]
        task_id = test_task["task_id"]
        
        # Update to In Progress
        db.collection(collection).document(task_id).update({
            "status": "In Progress",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify
        doc = db.collection(collection).document(task_id).get()
        assert doc.to_dict()["status"] == "In Progress"
        
        # Update to Done
        db.collection(collection).document(task_id).update({
            "status": "Done",
            "completed_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify
        doc = db.collection(collection).document(task_id).get()
        assert doc.to_dict()["status"] == "Done"
        assert "completed_at" in doc.to_dict()


class TestTaskQueries:
    """Test querying tasks with various filters."""
    
    def test_query_tasks_by_status(self, db, test_collection_prefix, cleanup_collections):
        """Test querying tasks by status."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        # Create tasks with different statuses
        todo_ids = []
        done_ids = []
        
        for i in range(2):
            task_id = f"todo_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(collection_name).document(task_id).set({
                "task_id": task_id,
                "title": f"Todo Task {i}",
                "status": "To Do"
            })
            todo_ids.append(task_id)
        
        for i in range(2):
            task_id = f"done_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(collection_name).document(task_id).set({
                "task_id": task_id,
                "title": f"Done Task {i}",
                "status": "Done"
            })
            done_ids.append(task_id)
        
        # Query To Do tasks
        todo_query = db.collection(collection_name).where(filter=FieldFilter("status", "==", "To Do"))
        todo_tasks = [doc.to_dict() for doc in todo_query.stream()]
        
        assert len(todo_tasks) >= 2
        todo_task_ids = [t["task_id"] for t in todo_tasks]
        for task_id in todo_ids:
            assert task_id in todo_task_ids
        
        # Cleanup
        for task_id in todo_ids + done_ids:
            db.collection(collection_name).document(task_id).delete()


class TestTaskWithLabels:
    """Test task label operations."""
    
    def test_add_labels_to_task(self, db, test_task):
        """Test adding labels to a task."""
        collection = test_task["collection"]
        task_id = test_task["task_id"]
        
        labels = ["bug", "urgent", "frontend"]
        
        db.collection(collection).document(task_id).update({
            "labels": labels
        })
        
        doc = db.collection(collection).document(task_id).get()
        assert "labels" in doc.to_dict()
        assert set(doc.to_dict()["labels"]) == set(labels)


class TestTaskPriority:
    """Test task priority handling."""
    
    def test_create_tasks_with_different_priorities(self, db, test_collection_prefix, cleanup_collections):
        """Test creating tasks with various priority levels."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        priorities = [1, 3, 5, 7, 10]
        task_ids = []
        
        for priority in priorities:
            task_id = f"priority_{priority}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(collection_name).document(task_id).set({
                "task_id": task_id,
                "title": f"Priority {priority} Task",
                "status": "To Do",
                "priority": priority,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            task_ids.append(task_id)
        
        # Query and verify priorities
        for task_id, expected_priority in zip(task_ids, priorities):
            doc = db.collection(collection_name).document(task_id).get()
            assert doc.exists
            assert doc.to_dict()["priority"] == expected_priority
        
        # Cleanup
        for task_id in task_ids:
            db.collection(collection_name).document(task_id).delete()
    
    
    def test_update_task_priority(self, db, test_task):
        """Test updating task priority."""
        collection = test_task["collection"]
        task_id = test_task["task_id"]
        
        # Update priority from 5 to 10
        db.collection(collection).document(task_id).update({
            "priority": 10,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify
        doc = db.collection(collection).document(task_id).get()
        assert doc.to_dict()["priority"] == 10


class TestTaskAssignment:
    """Test task assignment functionality."""
    
    def test_assign_task_to_user(self, db, test_collection_prefix, cleanup_collections):
        """Test assigning a task to a specific user."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        users_collection = f"{test_collection_prefix}_users"
        
        for col in [tasks_collection, users_collection]:
            cleanup_collections.append(col)
        
        # Create user
        user_id = "assignee_001"
        db.collection(users_collection).document(user_id).set({
            "user_id": user_id,
            "name": "Test Assignee",
            "email": "assignee@test.com"
        })
        
        # Create task
        task_id = f"assign_task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Task to Assign",
            "status": "To Do",
            "priority": 5,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Assign task
        db.collection(tasks_collection).document(task_id).update({
            "assigned_to": {
                "user_id": user_id,
                "name": "Test Assignee"
            }
        })
        
        # Verify assignment
        task_doc = db.collection(tasks_collection).document(task_id).get()
        task_data = task_doc.to_dict()
        assert "assigned_to" in task_data
        assert task_data["assigned_to"]["user_id"] == user_id
        
        # Cleanup
        db.collection(users_collection).document(user_id).delete()
        db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_reassign_task(self, db, test_collection_prefix, cleanup_collections):
        """Test reassigning a task from one user to another."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        users_collection = f"{test_collection_prefix}_users"
        
        for col in [tasks_collection, users_collection]:
            cleanup_collections.append(col)
        
        # Create users
        user1_id = "assignee_001"
        user2_id = "assignee_002"
        
        for user_id, name in [(user1_id, "User 1"), (user2_id, "User 2")]:
            db.collection(users_collection).document(user_id).set({
                "user_id": user_id,
                "name": name,
                "email": f"{user_id}@test.com"
            })
        
        # Create task assigned to user 1
        task_id = f"reassign_task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Task to Reassign",
            "status": "To Do",
            "priority": 5,
            "assigned_to": {"user_id": user1_id, "name": "User 1"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify initial assignment
        task_doc = db.collection(tasks_collection).document(task_id).get()
        assert task_doc.to_dict()["assigned_to"]["user_id"] == user1_id
        
        # Reassign to user 2
        db.collection(tasks_collection).document(task_id).update({
            "assigned_to": {"user_id": user2_id, "name": "User 2"},
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify reassignment
        task_doc = db.collection(tasks_collection).document(task_id).get()
        assert task_doc.to_dict()["assigned_to"]["user_id"] == user2_id
        
        # Cleanup
        for user_id in [user1_id, user2_id]:
            db.collection(users_collection).document(user_id).delete()
        db.collection(tasks_collection).document(task_id).delete()


class TestTaskDueDates:
    """Test task due date handling."""
    
    def test_create_task_with_due_date(self, db, test_collection_prefix, cleanup_collections):
        """Test creating a task with a future due date."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        task_id = f"due_date_task_{datetime.now(timezone.utc).timestamp()}"
        due_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        
        db.collection(collection_name).document(task_id).set({
            "task_id": task_id,
            "title": "Task with Due Date",
            "status": "To Do",
            "priority": 5,
            "due_date": due_date,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify
        doc = db.collection(collection_name).document(task_id).get()
        assert doc.exists
        assert doc.to_dict()["due_date"] == due_date
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
    
    
    def test_update_task_due_date(self, db, test_task):
        """Test updating a task's due date."""
        collection = test_task["collection"]
        task_id = test_task["task_id"]
        
        new_due_date = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        
        db.collection(collection).document(task_id).update({
            "due_date": new_due_date,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify
        doc = db.collection(collection).document(task_id).get()
        assert doc.to_dict()["due_date"] == new_due_date
    
    
    def test_overdue_task_detection(self, db, test_collection_prefix, cleanup_collections):
        """Test identifying overdue tasks."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        now = datetime.now(timezone.utc)
        
        # Create overdue task
        overdue_id = f"overdue_{now.timestamp()}"
        db.collection(collection_name).document(overdue_id).set({
            "task_id": overdue_id,
            "title": "Overdue Task",
            "status": "To Do",
            "due_date": (now - timedelta(days=3)).isoformat(),
            "created_at": now.isoformat()
        })
        
        # Create future task
        future_id = f"future_{now.timestamp()}"
        db.collection(collection_name).document(future_id).set({
            "task_id": future_id,
            "title": "Future Task",
            "status": "To Do",
            "due_date": (now + timedelta(days=3)).isoformat(),
            "created_at": now.isoformat()
        })
        
        # Query all tasks and categorize
        all_tasks = db.collection(collection_name).stream()
        overdue_tasks = []
        
        for doc in all_tasks:
            task = doc.to_dict()
            if task.get("due_date") and task.get("status") != "Done":
                due_dt = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00'))
                if due_dt < now:
                    overdue_tasks.append(task)
        
        # Verify overdue task is detected
        overdue_ids = [t["task_id"] for t in overdue_tasks]
        assert overdue_id in overdue_ids
        assert future_id not in overdue_ids
        
        # Cleanup
        db.collection(collection_name).document(overdue_id).delete()
        db.collection(collection_name).document(future_id).delete()


class TestTaskDeletion:
    """Test task deletion functionality."""
    
    def test_delete_task(self, db, test_collection_prefix, cleanup_collections):
        """Test deleting a task from Firestore."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        task_id = f"delete_task_{datetime.now(timezone.utc).timestamp()}"
        
        # Create task
        db.collection(collection_name).document(task_id).set({
            "task_id": task_id,
            "title": "Task to Delete",
            "status": "To Do",
            "priority": 5
        })
        
        # Verify creation
        doc = db.collection(collection_name).document(task_id).get()
        assert doc.exists
        
        # Delete task
        db.collection(collection_name).document(task_id).delete()
        
        # Verify deletion
        doc = db.collection(collection_name).document(task_id).get()
        assert not doc.exists
    
    
    def test_archive_task_instead_of_delete(self, db, test_task):
        """Test archiving a task instead of permanent deletion."""
        collection = test_task["collection"]
        task_id = test_task["task_id"]
        
        # Archive task
        db.collection(collection).document(task_id).update({
            "archived": True,
            "archived_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify task still exists but is archived
        doc = db.collection(collection).document(task_id).get()
        assert doc.exists
        task_data = doc.to_dict()
        assert task_data.get("archived") is True
        assert "archived_at" in task_data


class TestTaskComplexWorkflows:
    """Test complex task workflows."""
    
    def test_complete_task_workflow(self, db, test_collection_prefix, cleanup_collections):
        """Test complete workflow: create -> assign -> update -> complete."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        users_collection = f"{test_collection_prefix}_users"
        
        for col in [tasks_collection, users_collection]:
            cleanup_collections.append(col)
        
        # Create user
        user_id = "workflow_user"
        db.collection(users_collection).document(user_id).set({
            "user_id": user_id,
            "name": "Workflow User",
            "email": "workflow@test.com"
        })
        
        # Step 1: Create task
        task_id = f"workflow_task_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Workflow Task",
            "status": "To Do",
            "priority": 5,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify creation
        doc = db.collection(tasks_collection).document(task_id).get()
        assert doc.exists
        assert doc.to_dict()["status"] == "To Do"
        
        # Step 2: Assign task
        db.collection(tasks_collection).document(task_id).update({
            "assigned_to": {"user_id": user_id, "name": "Workflow User"}
        })
        
        doc = db.collection(tasks_collection).document(task_id).get()
        assert doc.to_dict()["assigned_to"]["user_id"] == user_id
        
        # Step 3: Update to In Progress
        db.collection(tasks_collection).document(task_id).update({
            "status": "In Progress",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        doc = db.collection(tasks_collection).document(task_id).get()
        assert doc.to_dict()["status"] == "In Progress"
        
        # Step 4: Complete task
        db.collection(tasks_collection).document(task_id).update({
            "status": "Done",
            "completed_at": datetime.now(timezone.utc).isoformat()
        })
        
        doc = db.collection(tasks_collection).document(task_id).get()
        task_data = doc.to_dict()
        assert task_data["status"] == "Done"
        assert "completed_at" in task_data
        
        # Cleanup
        db.collection(users_collection).document(user_id).delete()
        db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_task_with_multiple_updates(self, db, test_task):
        """Test task with multiple sequential updates."""
        collection = test_task["collection"]
        task_id = test_task["task_id"]
        
        updates = [
            {"priority": 7, "field": "priority"},
            {"status": "In Progress", "field": "status"},
            {"priority": 10, "field": "priority"},
            {"description": "Updated description", "field": "description"},
        ]
        
        for update in updates:
            db.collection(collection).document(task_id).update({
                update["field"]: update[update["field"]],
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        
        # Verify final state
        doc = db.collection(collection).document(task_id).get()
        task_data = doc.to_dict()
        assert task_data["priority"] == 10
        assert task_data["status"] == "In Progress"
        assert task_data["description"] == "Updated description"


class TestTaskQueryFiltering:
    """Test complex task query filtering."""
    
    def test_query_tasks_by_multiple_criteria(self, db, test_collection_prefix, cleanup_collections):
        """Test querying tasks with multiple filter criteria."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        # Create tasks with various attributes
        tasks_data = [
            {"task_id": "filter_1", "status": "To Do", "priority": 10, "labels": ["urgent"]},
            {"task_id": "filter_2", "status": "To Do", "priority": 5, "labels": ["normal"]},
            {"task_id": "filter_3", "status": "Done", "priority": 10, "labels": ["urgent"]},
            {"task_id": "filter_4", "status": "In Progress", "priority": 7, "labels": ["important"]},
        ]
        
        for task_data in tasks_data:
            task_data["title"] = f"Task {task_data['task_id']}"
            task_data["created_at"] = datetime.now(timezone.utc).isoformat()
            db.collection(collection_name).document(task_data["task_id"]).set(task_data)
        
        # Query: To Do status
        todo_query = db.collection(collection_name).where(
            filter=FieldFilter("status", "==", "To Do")
        )
        todo_tasks = [doc.to_dict() for doc in todo_query.stream()]
        assert len(todo_tasks) == 2
        
        # Client-side filter for high priority (>= 7)
        all_tasks_stream = db.collection(collection_name).stream()
        all_tasks = [doc.to_dict() for doc in all_tasks_stream]
        high_priority = [t for t in all_tasks if t.get("priority", 0) >= 7]
        assert len(high_priority) == 3
        
        # Cleanup
        for task_data in tasks_data:
            db.collection(collection_name).document(task_data["task_id"]).delete()


class TestTaskEdgeCases:
    """Test edge cases for task operations."""
    
    def test_task_with_minimal_data(self, db, test_collection_prefix, cleanup_collections):
        """Test creating task with only required fields."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        task_id = f"minimal_{datetime.now(timezone.utc).timestamp()}"
        
        # Create task with minimal data
        db.collection(collection_name).document(task_id).set({
            "task_id": task_id,
            "title": "Minimal Task"
        })
        
        # Verify
        doc = db.collection(collection_name).document(task_id).get()
        assert doc.exists
        task_data = doc.to_dict()
        assert task_data["task_id"] == task_id
        assert task_data["title"] == "Minimal Task"
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
    
    
    def test_task_with_all_optional_fields(self, db, test_collection_prefix, cleanup_collections):
        """Test creating task with all possible fields populated."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        task_id = f"complete_{datetime.now(timezone.utc).timestamp()}"
        now = datetime.now(timezone.utc)
        
        comprehensive_task = {
            "task_id": task_id,
            "title": "Comprehensive Task",
            "description": "Task with all fields",
            "status": "In Progress",
            "priority": 8,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "due_date": (now + timedelta(days=5)).isoformat(),
            "created_by": {"user_id": "creator_001", "name": "Creator"},
            "assigned_to": {"user_id": "assignee_001", "name": "Assignee"},
            "project_id": "project_001",
            "labels": ["feature", "high-priority", "backend"],
            "tags": ["sprint-1", "q4"],
            "estimated_hours": 8,
            "actual_hours": 0,
            "archived": False,
            "is_recurring": False
        }
        
        db.collection(collection_name).document(task_id).set(comprehensive_task)
        
        # Verify all fields
        doc = db.collection(collection_name).document(task_id).get()
        task_data = doc.to_dict()
        
        for key, value in comprehensive_task.items():
            assert key in task_data
            assert task_data[key] == value
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
    
    
    def test_task_with_special_characters_in_title(self, db, test_collection_prefix, cleanup_collections):
        """Test task with special characters and unicode in title."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        task_id = f"special_{datetime.now(timezone.utc).timestamp()}"
        special_title = "Task with émojis 🎉 & symbols: @#$%^&*()!"
        
        db.collection(collection_name).document(task_id).set({
            "task_id": task_id,
            "title": special_title,
            "status": "To Do"
        })
        
        # Verify
        doc = db.collection(collection_name).document(task_id).get()
        assert doc.to_dict()["title"] == special_title
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
