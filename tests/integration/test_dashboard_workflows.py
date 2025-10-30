"""Integration tests for dashboard workflows using real Firebase."""
import pytest
import json
from datetime import datetime, timezone, timedelta
from google.cloud.firestore_v1.base_query import FieldFilter


class TestDashboardData:
    """Test dashboard data queries with real Firebase."""
    
    def test_query_user_tasks(self, db, test_collection_prefix, cleanup_collections):
        """Test querying tasks assigned to a specific user."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        user_id = "test_user_123"
        task_ids = []
        
        # Create tasks assigned to user
        for i in range(3):
            task_id = f"user_task_{i}_{datetime.now(timezone.utc).timestamp()}"
            db.collection(collection_name).document(task_id).set({
                "task_id": task_id,
                "title": f"User Task {i}",
                "assigned_to": user_id,
                "status": "In Progress"
            })
            task_ids.append(task_id)
        
        # Query tasks assigned to user
        query = db.collection(collection_name).where(filter=FieldFilter("assigned_to", "==", user_id))
        user_tasks = [doc.to_dict() for doc in query.stream()]
        
        assert len(user_tasks) >= 3
        retrieved_ids = [t["task_id"] for t in user_tasks]
        for task_id in task_ids:
            assert task_id in retrieved_ids
        
        # Cleanup
        for task_id in task_ids:
            db.collection(collection_name).document(task_id).delete()
    
    
    def test_query_tasks_by_due_date(self, db, test_collection_prefix, cleanup_collections):
        """Test querying tasks by due date range."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        # Create tasks with different due dates
        today = datetime.now(timezone.utc)
        overdue_id = f"overdue_{today.timestamp()}"
        upcoming_id = f"upcoming_{today.timestamp()}"
        
        # Overdue task
        db.collection(collection_name).document(overdue_id).set({
            "task_id": overdue_id,
            "title": "Overdue Task",
            "due_date": (today - timedelta(days=2)).isoformat(),
            "status": "To Do"
        })
        
        # Upcoming task
        db.collection(collection_name).document(upcoming_id).set({
            "task_id": upcoming_id,
            "title": "Upcoming Task",
            "due_date": (today + timedelta(days=3)).isoformat(),
            "status": "To Do"
        })
        
        # Verify data creation
        overdue_doc = db.collection(collection_name).document(overdue_id).get()
        upcoming_doc = db.collection(collection_name).document(upcoming_id).get()
        
        assert overdue_doc.exists
        assert upcoming_doc.exists
        
        # Cleanup
        db.collection(collection_name).document(overdue_id).delete()
        db.collection(collection_name).document(upcoming_id).delete()


class TestDashboardTimelineGrouping:
    """Test timeline grouping functionality from unit tests."""
    
    def test_completed_tasks_excluded_from_timeline(self, db, test_collection_prefix, cleanup_collections):
        """Test that completed tasks are excluded from timeline view."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        # Create completed overdue task
        task_id = f"completed_overdue_{datetime.now(timezone.utc).timestamp()}"
        db.collection(collection_name).document(task_id).set({
            "task_id": task_id,
            "title": "Completed Overdue Task",
            "status": "Done",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Query all tasks and filter for timeline
        all_tasks = db.collection(collection_name).stream()
        timeline_tasks = [
            doc.to_dict() for doc in all_tasks 
            if doc.to_dict().get("status") != "Done"
        ]
        
        # Verify completed task is excluded
        timeline_task_ids = [t["task_id"] for t in timeline_tasks]
        assert task_id not in timeline_task_ids
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
    
    
    def test_today_vs_this_week_categorization(self, db, test_collection_prefix, cleanup_collections):
        """Test proper categorization of tasks due today vs this week."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        now = datetime.now(timezone.utc)
        
        # Create task due today
        today_id = f"today_{now.timestamp()}"
        db.collection(collection_name).document(today_id).set({
            "task_id": today_id,
            "title": "Due Today",
            "status": "In Progress",
            "due_date": now.isoformat()
        })
        
        # Create task due in 3 days
        week_id = f"week_{now.timestamp()}"
        db.collection(collection_name).document(week_id).set({
            "task_id": week_id,
            "title": "Due This Week",
            "status": "To Do",
            "due_date": (now + timedelta(days=3)).isoformat()
        })
        
        # Categorize tasks
        all_tasks_stream = db.collection(collection_name).stream()
        categories = {"today": [], "this_week": []}
        
        for doc in all_tasks_stream:
            task = doc.to_dict()
            due_date_str = task.get("due_date")
            if not due_date_str:
                continue
            
            due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            days_until_due = (due_date - now).days
            
            if days_until_due == 0:
                categories["today"].append(task)
            elif 1 <= days_until_due <= 7:
                categories["this_week"].append(task)
        
        # Verify categorization
        today_task_ids = [t["task_id"] for t in categories["today"]]
        week_task_ids = [t["task_id"] for t in categories["this_week"]]
        
        assert today_id in today_task_ids
        assert week_id in week_task_ids
        
        # Cleanup
        db.collection(collection_name).document(today_id).delete()
        db.collection(collection_name).document(week_id).delete()
    
    
    def test_overdue_incomplete_task_categorization(self, db, test_collection_prefix, cleanup_collections):
        """Test that overdue incomplete tasks are properly categorized."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        task_id = f"overdue_{datetime.now(timezone.utc).timestamp()}"
        db.collection(collection_name).document(task_id).set({
            "task_id": task_id,
            "title": "Overdue Incomplete",
            "status": "In Progress",
            "priority": 8,
            "due_date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        })
        
        # Query and categorize
        doc = db.collection(collection_name).document(task_id).get()
        task = doc.to_dict()
        
        due_date = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00'))
        is_overdue = due_date < datetime.now(timezone.utc) and task["status"] != "Done"
        
        assert is_overdue
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
    
    
    def test_no_due_date_task_categorization(self, db, test_collection_prefix, cleanup_collections):
        """Test tasks with no due date are handled correctly."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        task_id = f"no_due_date_{datetime.now(timezone.utc).timestamp()}"
        db.collection(collection_name).document(task_id).set({
            "task_id": task_id,
            "title": "No Due Date Task",
            "status": "To Do",
            "priority": 5,
            "due_date": None
        })
        
        # Query and verify
        doc = db.collection(collection_name).document(task_id).get()
        task = doc.to_dict()
        
        assert task.get("due_date") is None
        
        # Such tasks should go to a separate category
        has_due_date = task.get("due_date") is not None
        assert not has_due_date
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
    
    
    def test_blocked_overdue_task_still_shows_overdue(self, db, test_collection_prefix, cleanup_collections):
        """Test that blocked tasks that are overdue still show as overdue."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        task_id = f"blocked_overdue_{datetime.now(timezone.utc).timestamp()}"
        db.collection(collection_name).document(task_id).set({
            "task_id": task_id,
            "title": "Blocked Overdue Task",
            "status": "Blocked",
            "priority": 7,
            "due_date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        })
        
        # Query and verify
        doc = db.collection(collection_name).document(task_id).get()
        task = doc.to_dict()
        
        due_date = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00'))
        is_overdue = due_date < datetime.now(timezone.utc) and task["status"] != "Done"
        
        # Should still be overdue even though blocked
        assert is_overdue
        assert task["status"] == "Blocked"
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
    
    
    def test_edge_case_exactly_7_days_future(self, db, test_collection_prefix, cleanup_collections):
        """Test task due exactly 7 days in future is categorized as 'this week'."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        now = datetime.now(timezone.utc)
        task_id = f"seven_days_{now.timestamp()}"
        
        db.collection(collection_name).document(task_id).set({
            "task_id": task_id,
            "title": "Seven Days Future",
            "status": "To Do",
            "due_date": (now + timedelta(days=7)).isoformat()
        })
        
        # Categorize
        doc = db.collection(collection_name).document(task_id).get()
        task = doc.to_dict()
        
        due_date = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00'))
        days_diff = (due_date - now).days
        
        # Should be categorized as "this week" (<=7 days)
        is_this_week = 1 <= days_diff <= 7
        assert is_this_week
        
        # Cleanup
        db.collection(collection_name).document(task_id).delete()
    
    
    def test_detect_conflicts_with_multiple_tasks_same_date(self, db, test_collection_prefix, cleanup_collections):
        """Test conflict detection when multiple tasks have same due date."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        conflict_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        task_ids = []
        
        # Create 3 tasks with same due date - use index to ensure unique IDs
        base_timestamp = datetime.now(timezone.utc).timestamp()
        for i in range(3):
            task_id = f"conflict_{i}_{base_timestamp}_{i}"  # Add index twice for uniqueness
            db.collection(collection_name).document(task_id).set({
                "task_id": task_id,
                "title": f"Conflict Task {i}",
                "status": "To Do",
                "due_date": conflict_date
            })
            task_ids.append(task_id)
        
        # Detect conflicts
        all_tasks_stream = db.collection(collection_name).stream()
        date_groups = {}
        
        for doc in all_tasks_stream:
            task = doc.to_dict()
            due_date = task.get("due_date")
            if due_date:
                date_key = due_date.split('T')[0]
                if date_key not in date_groups:
                    date_groups[date_key] = []
                date_groups[date_key].append(task)
        
        # Find conflicts (multiple tasks on same date)
        conflicts = [
            {"date": date_key, "count": len(tasks), "tasks": tasks}
            for date_key, tasks in date_groups.items()
            if len(tasks) > 1
        ]
        
        # Verify conflict detected
        assert len(conflicts) >= 1
        conflict_date_key = conflict_date.split('T')[0]
        matching_conflicts = [c for c in conflicts if c["date"] == conflict_date_key]
        assert len(matching_conflicts) >= 1
        assert matching_conflicts[0]["count"] >= 3
        
        # Cleanup
        for task_id in task_ids:
            db.collection(collection_name).document(task_id).delete()


class TestDashboardStatistics:
    """Test dashboard statistics calculation."""
    
    def test_overdue_count_excludes_completed(self, db, test_collection_prefix, cleanup_collections):
        """Test that overdue count excludes completed tasks."""
        collection_name = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(collection_name)
        
        now = datetime.now(timezone.utc)
        task_ids = []
        
        # Create overdue incomplete task
        incomplete_id = f"overdue_incomplete_{now.timestamp()}"
        db.collection(collection_name).document(incomplete_id).set({
            "task_id": incomplete_id,
            "title": "Overdue Incomplete",
            "status": "In Progress",
            "due_date": (now - timedelta(days=3)).isoformat()
        })
        task_ids.append(incomplete_id)
        
        # Create overdue completed task
        completed_id = f"overdue_complete_{now.timestamp()}"
        db.collection(collection_name).document(completed_id).set({
            "task_id": completed_id,
            "title": "Overdue Complete",
            "status": "Done",
            "due_date": (now - timedelta(days=2)).isoformat(),
            "completed_at": now.isoformat()
        })
        task_ids.append(completed_id)
        
        # Calculate overdue count
        all_tasks_stream = db.collection(collection_name).stream()
        overdue_tasks = []
        
        for doc in all_tasks_stream:
            task = doc.to_dict()
            due_date_str = task.get("due_date")
            status = task.get("status")
            
            if due_date_str and status != "Done":
                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                if due_date < now:
                    overdue_tasks.append(task)
        
        # Verify only incomplete overdue task is counted
        overdue_task_ids = [t["task_id"] for t in overdue_tasks]
        assert incomplete_id in overdue_task_ids
        assert completed_id not in overdue_task_ids
        
        # Cleanup
        for task_id in task_ids:
            db.collection(collection_name).document(task_id).delete()
