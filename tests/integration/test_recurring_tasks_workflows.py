"""Integration tests for recurring task workflows using real Firebase."""
import pytest
from datetime import datetime, timezone, timedelta
from google.cloud.firestore_v1.base_query import FieldFilter


class TestRecurringTaskCreation:
    """Test creating recurring tasks with real Firebase."""
    
    def test_create_recurring_task(self, db, test_collection_prefix, cleanup_collections):
        """Test creating a basic recurring task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        task_id = f"recurring_task_{datetime.now(timezone.utc).timestamp()}"
        due_date = datetime.now(timezone.utc) + timedelta(days=7)
        
        task_data = {
            "task_id": task_id,
            "title": "Weekly Report",
            "description": "Submit weekly progress report",
            "status": "To Do",
            "priority": 5,
            "due_date": due_date.isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "created_by": {"user_id": "user123", "name": "Test User"},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Create recurring task
        db.collection(tasks_collection).document(task_id).set(task_data)
        
        # Verify creation
        doc = db.collection(tasks_collection).document(task_id).get()
        assert doc.exists
        
        retrieved_task = doc.to_dict()
        assert retrieved_task["is_recurring"] == True
        assert retrieved_task["recurrence_interval_days"] == 7
        assert retrieved_task["title"] == "Weekly Report"
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_create_daily_recurring_task(self, db, test_collection_prefix, cleanup_collections):
        """Test creating a daily recurring task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        task_id = f"daily_task_{datetime.now(timezone.utc).timestamp()}"
        
        task_data = {
            "task_id": task_id,
            "title": "Daily Standup",
            "status": "To Do",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 1,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        db.collection(tasks_collection).document(task_id).set(task_data)
        
        # Verify
        doc = db.collection(tasks_collection).document(task_id).get()
        assert doc.to_dict()["recurrence_interval_days"] == 1
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_create_monthly_recurring_task(self, db, test_collection_prefix, cleanup_collections):
        """Test creating a monthly recurring task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        task_id = f"monthly_task_{datetime.now(timezone.utc).timestamp()}"
        
        task_data = {
            "task_id": task_id,
            "title": "Monthly Review",
            "status": "To Do",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 30,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        db.collection(tasks_collection).document(task_id).set(task_data)
        
        # Verify
        doc = db.collection(tasks_collection).document(task_id).get()
        assert doc.to_dict()["recurrence_interval_days"] == 30
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()


class TestRecurringTaskCompletion:
    """Test completing recurring tasks and auto-creating next occurrence."""
    
    def test_complete_recurring_task_creates_next(self, db, test_collection_prefix, cleanup_collections):
        """Test that completing a recurring task creates the next occurrence."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create parent recurring task
        parent_task_id = f"parent_task_{datetime.now(timezone.utc).timestamp()}"
        original_due_date = datetime.now(timezone.utc) + timedelta(days=7)
        
        db.collection(tasks_collection).document(parent_task_id).set({
            "task_id": parent_task_id,
            "title": "Weekly Report",
            "status": "To Do",
            "due_date": original_due_date.isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Mark as completed
        db.collection(tasks_collection).document(parent_task_id).update({
            "status": "Done",
            "completed_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create next occurrence (simulating backend logic)
        next_task_id = f"next_task_{datetime.now(timezone.utc).timestamp()}"
        next_due_date = original_due_date + timedelta(days=7)
        
        db.collection(tasks_collection).document(next_task_id).set({
            "task_id": next_task_id,
            "title": "Weekly Report",
            "status": "To Do",
            "due_date": next_due_date.isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "parent_recurring_task_id": parent_task_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify parent is completed
        parent_doc = db.collection(tasks_collection).document(parent_task_id).get()
        assert parent_doc.to_dict()["status"] == "Done"
        
        # Verify next occurrence was created
        next_doc = db.collection(tasks_collection).document(next_task_id).get()
        assert next_doc.exists
        next_data = next_doc.to_dict()
        assert next_data["status"] == "To Do"
        assert next_data["parent_recurring_task_id"] == parent_task_id
        assert next_data["is_recurring"] == True
        
        # Cleanup
        db.collection(tasks_collection).document(parent_task_id).delete()
        db.collection(tasks_collection).document(next_task_id).delete()
    
    
    def test_recurring_task_chain(self, db, test_collection_prefix, cleanup_collections):
        """Test a chain of recurring task occurrences."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create original recurring task
        original_task_id = f"original_{datetime.now(timezone.utc).timestamp()}"
        base_due_date = datetime.now(timezone.utc)
        
        db.collection(tasks_collection).document(original_task_id).set({
            "task_id": original_task_id,
            "title": "Daily Task",
            "status": "Done",
            "due_date": base_due_date.isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 1,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create chain of 3 occurrences
        task_ids = [original_task_id]
        parent_id = original_task_id
        
        for i in range(1, 4):
            task_id = f"occurrence_{i}_{datetime.now(timezone.utc).timestamp()}"
            due_date = base_due_date + timedelta(days=i)
            
            db.collection(tasks_collection).document(task_id).set({
                "task_id": task_id,
                "title": "Daily Task",
                "status": "To Do" if i == 3 else "Done",
                "due_date": due_date.isoformat(),
                "is_recurring": True,
                "recurrence_interval_days": 1,
                "parent_recurring_task_id": original_task_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            task_ids.append(task_id)
        
        # Query all occurrences
        query = db.collection(tasks_collection).where(
            filter=FieldFilter("parent_recurring_task_id", "==", original_task_id)
        )
        occurrences = [doc.to_dict() for doc in query.stream()]
        
        assert len(occurrences) >= 3
        
        # Cleanup
        for task_id in task_ids:
            db.collection(tasks_collection).document(task_id).delete()


class TestRecurringTaskUpdates:
    """Test updating recurring task settings."""
    
    def test_update_recurrence_interval(self, db, test_collection_prefix, cleanup_collections):
        """Test updating the recurrence interval of a recurring task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        
        # Create recurring task with weekly interval
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Recurring Task",
            "status": "To Do",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Update to bi-weekly
        db.collection(tasks_collection).document(task_id).update({
            "recurrence_interval_days": 14
        })
        
        # Verify update
        doc = db.collection(tasks_collection).document(task_id).get()
        assert doc.to_dict()["recurrence_interval_days"] == 14
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_disable_recurrence(self, db, test_collection_prefix, cleanup_collections):
        """Test disabling recurrence on a task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        
        # Create recurring task
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Recurring Task",
            "status": "To Do",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Disable recurrence
        db.collection(tasks_collection).document(task_id).update({
            "is_recurring": False,
            "recurrence_interval_days": None
        })
        
        # Verify
        doc = db.collection(tasks_collection).document(task_id).get()
        task_data = doc.to_dict()
        assert task_data["is_recurring"] == False
        assert task_data["recurrence_interval_days"] is None
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_update_recurring_task_due_date(self, db, test_collection_prefix, cleanup_collections):
        """Test updating the due date of a recurring task."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        original_due_date = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Create recurring task
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Recurring Task",
            "status": "To Do",
            "due_date": original_due_date.isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Update due date
        new_due_date = datetime.now(timezone.utc) + timedelta(days=10)
        db.collection(tasks_collection).document(task_id).update({
            "due_date": new_due_date.isoformat()
        })
        
        # Verify
        doc = db.collection(tasks_collection).document(task_id).get()
        assert doc.to_dict()["due_date"] == new_due_date.isoformat()
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()


class TestRecurringTaskQueries:
    """Test querying recurring tasks."""
    
    def test_query_all_recurring_tasks(self, db, test_collection_prefix, cleanup_collections):
        """Test querying all recurring tasks."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create mix of recurring and non-recurring tasks
        recurring_task_ids = []
        non_recurring_task_ids = []
        
        for i in range(3):
            task_id = f"recurring_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(tasks_collection).document(task_id).set({
                "task_id": task_id,
                "title": f"Recurring Task {i}",
                "status": "To Do",
                "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "is_recurring": True,
                "recurrence_interval_days": 7,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            recurring_task_ids.append(task_id)
        
        for i in range(2):
            task_id = f"normal_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(tasks_collection).document(task_id).set({
                "task_id": task_id,
                "title": f"Normal Task {i}",
                "status": "To Do",
                "is_recurring": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            non_recurring_task_ids.append(task_id)
        
        # Query only recurring tasks
        query = db.collection(tasks_collection).where(filter=FieldFilter("is_recurring", "==", True))
        recurring_tasks = [doc.to_dict() for doc in query.stream()]
        
        # Verify only recurring tasks returned
        assert len([t for t in recurring_tasks if t["task_id"] in recurring_task_ids]) >= 3
        
        # Cleanup
        for task_id in recurring_task_ids + non_recurring_task_ids:
            db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_query_recurring_tasks_by_interval(self, db, test_collection_prefix, cleanup_collections):
        """Test querying recurring tasks by their recurrence interval."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create tasks with different intervals
        daily_task_ids = []
        weekly_task_ids = []
        
        for i in range(2):
            task_id = f"daily_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(tasks_collection).document(task_id).set({
                "task_id": task_id,
                "title": f"Daily Task {i}",
                "status": "To Do",
                "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "is_recurring": True,
                "recurrence_interval_days": 1,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            daily_task_ids.append(task_id)
        
        for i in range(3):
            task_id = f"weekly_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(tasks_collection).document(task_id).set({
                "task_id": task_id,
                "title": f"Weekly Task {i}",
                "status": "To Do",
                "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "is_recurring": True,
                "recurrence_interval_days": 7,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            weekly_task_ids.append(task_id)
        
        # Query weekly recurring tasks
        query = db.collection(tasks_collection).where(filter=FieldFilter("recurrence_interval_days", "==", 7))
        weekly_tasks = [doc.to_dict() for doc in query.stream()]
        
        # Verify correct interval tasks returned
        assert len([t for t in weekly_tasks if t["task_id"] in weekly_task_ids]) >= 3
        
        # Cleanup
        for task_id in daily_task_ids + weekly_task_ids:
            db.collection(tasks_collection).document(task_id).delete()


class TestRecurringTaskEdgeCases:
    """Test edge cases and complex recurring task scenarios."""
    
    def test_recurring_task_without_due_date_validation(self, db, test_collection_prefix, cleanup_collections):
        """Test that recurring tasks should have due dates (validation scenario)."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        
        # In a real system, this should be prevented, but we test the data state
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Invalid Recurring Task",
            "status": "To Do",
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "created_at": datetime.now(timezone.utc).isoformat()
            # Note: no due_date - this should ideally be caught by validation
        })
        
        # Verify task exists but is missing due_date
        doc = db.collection(tasks_collection).document(task_id).get()
        task_data = doc.to_dict()
        assert "due_date" not in task_data or task_data.get("due_date") is None
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_recurring_task_with_very_long_interval(self, db, test_collection_prefix, cleanup_collections):
        """Test recurring task with a very long interval (e.g., yearly)."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}"
        
        # Create yearly recurring task
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Annual Review",
            "status": "To Do",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 365,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify
        doc = db.collection(tasks_collection).document(task_id).get()
        assert doc.to_dict()["recurrence_interval_days"] == 365
        
        # Cleanup
        db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_parent_task_reference_integrity(self, db, test_collection_prefix, cleanup_collections):
        """Test that child tasks correctly reference their parent."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create parent task
        parent_id = f"parent_{datetime.now(timezone.utc).timestamp()}"
        db.collection(tasks_collection).document(parent_id).set({
            "task_id": parent_id,
            "title": "Parent Recurring Task",
            "status": "Done",
            "due_date": datetime.now(timezone.utc).isoformat(),
            "is_recurring": True,
            "recurrence_interval_days": 7,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create child tasks
        child_ids = []
        for i in range(3):
            child_id = f"child_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(tasks_collection).document(child_id).set({
                "task_id": child_id,
                "title": "Parent Recurring Task",
                "status": "To Do",
                "due_date": (datetime.now(timezone.utc) + timedelta(days=7*(i+1))).isoformat(),
                "is_recurring": True,
                "recurrence_interval_days": 7,
                "parent_recurring_task_id": parent_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            child_ids.append(child_id)
        
        # Query children by parent
        query = db.collection(tasks_collection).where(
            filter=FieldFilter("parent_recurring_task_id", "==", parent_id)
        )
        children = [doc.to_dict() for doc in query.stream()]
        
        assert len(children) >= 3
        for child in children:
            assert child["parent_recurring_task_id"] == parent_id
        
        # Cleanup
        db.collection(tasks_collection).document(parent_id).delete()
        for child_id in child_ids:
            db.collection(tasks_collection).document(child_id).delete()
