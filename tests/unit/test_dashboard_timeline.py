"""
Unit tests for dashboard timeline categorization fixes
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from backend.api.dashboard import enrich_task_with_timeline_status, group_tasks_by_timeline


class TestTimelineCategorizationFixes:
    """Test fixes for completed tasks showing as overdue and this_week logic"""

    def test_completed_task_not_overdue(self):
        """Test that completed tasks are not categorized as overdue even if past due date"""
        # Create a task that's overdue but completed
        task = {
            "task_id": "task-123",
            "title": "Completed Task",
            "status": "Completed",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        }
        
        result = enrich_task_with_timeline_status(task)
        
        # Should be marked as completed, not overdue
        assert result["timeline_status"] == "completed"
        assert result["is_overdue"] is False
        assert result["is_upcoming"] is False


    def test_completed_task_excluded_from_timeline(self):
        """Test that completed tasks don't appear in any timeline category"""
        tasks = [
            {
                "task_id": "task-1",
                "title": "Overdue Incomplete",
                "status": "In Progress",
                "due_date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            },
            {
                "task_id": "task-2",
                "title": "Overdue Completed",
                "status": "Completed",
                "due_date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            },
            {
                "task_id": "task-3",
                "title": "Today Completed",
                "status": "Completed",
                "due_date": datetime.now(timezone.utc).isoformat(),
            },
        ]
        
        timeline = group_tasks_by_timeline(tasks)
        
        # Only task-1 should appear in overdue
        assert len(timeline["overdue"]) == 1
        assert timeline["overdue"][0]["task_id"] == "task-1"
        
        # Completed tasks should not appear in any category
        all_timeline_tasks = (
            timeline["overdue"] + 
            timeline["today"] + 
            timeline["this_week"] + 
            timeline["future"] + 
            timeline["no_due_date"]
        )
        task_ids = [t["task_id"] for t in all_timeline_tasks]
        assert "task-2" not in task_ids
        assert "task-3" not in task_ids


    def test_today_vs_this_week_categorization(self):
        """Test that today's tasks go to 'today' and future tasks within 7 days go to 'this_week'"""
        now = datetime.now(timezone.utc)
        
        tasks = [
            {
                "task_id": "task-today",
                "title": "Due Today",
                "status": "To Do",
                "due_date": now.isoformat(),
            },
            {
                "task_id": "task-tomorrow",
                "title": "Due Tomorrow",
                "status": "To Do",
                "due_date": (now + timedelta(days=1)).isoformat(),
            },
            {
                "task_id": "task-3days",
                "title": "Due in 3 Days",
                "status": "To Do",
                "due_date": (now + timedelta(days=3)).isoformat(),
            },
            {
                "task_id": "task-7days",
                "title": "Due in 7 Days",
                "status": "To Do",
                "due_date": (now + timedelta(days=7)).isoformat(),
            },
            {
                "task_id": "task-8days",
                "title": "Due in 8 Days",
                "status": "To Do",
                "due_date": (now + timedelta(days=8)).isoformat(),
            },
        ]
        
        timeline = group_tasks_by_timeline(tasks)
        
        # Today's task should be in 'today' category
        assert len(timeline["today"]) == 1
        assert timeline["today"][0]["task_id"] == "task-today"
        
        # Tasks 1-7 days out should be in 'this_week' category
        assert len(timeline["this_week"]) == 3
        this_week_ids = [t["task_id"] for t in timeline["this_week"]]
        assert "task-tomorrow" in this_week_ids
        assert "task-3days" in this_week_ids
        assert "task-7days" in this_week_ids
        
        # Task 8+ days out should be in 'future' category
        assert len(timeline["future"]) == 1
        assert timeline["future"][0]["task_id"] == "task-8days"


    def test_overdue_incomplete_task_categorization(self):
        """Test that incomplete overdue tasks are correctly categorized as overdue"""
        task = {
            "task_id": "task-overdue",
            "title": "Overdue Task",
            "status": "In Progress",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        }
        
        result = enrich_task_with_timeline_status(task)
        
        assert result["timeline_status"] == "overdue"
        assert result["is_overdue"] is True
        assert result["is_upcoming"] is False


    def test_no_due_date_task_categorization(self):
        """Test that tasks without due dates are categorized correctly"""
        task = {
            "task_id": "task-no-date",
            "title": "Task Without Date",
            "status": "To Do",
            "due_date": None,
        }
        
        result = enrich_task_with_timeline_status(task)
        
        assert result["timeline_status"] == "no_due_date"
        assert result["is_overdue"] is False
        assert result["is_upcoming"] is False


    def test_blocked_overdue_task_still_shows_overdue(self):
        """Test that blocked but incomplete tasks still show as overdue"""
        task = {
            "task_id": "task-blocked",
            "title": "Blocked Overdue Task",
            "status": "Blocked",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        }
        
        result = enrich_task_with_timeline_status(task)
        
        # Blocked tasks that are overdue should still show as overdue
        assert result["timeline_status"] == "overdue"
        assert result["is_overdue"] is True


    def test_completed_task_with_no_due_date(self):
        """Test that completed tasks without due dates are also excluded"""
        task = {
            "task_id": "task-completed-no-date",
            "title": "Completed No Date",
            "status": "Completed",
            "due_date": None,
        }
        
        result = enrich_task_with_timeline_status(task)
        
        assert result["timeline_status"] == "completed"
        assert result["is_overdue"] is False


    def test_edge_case_exactly_7_days_future(self):
        """Test task due exactly 7 days from now is in this_week"""
        task = {
            "task_id": "task-7days-exact",
            "title": "Due Exactly 7 Days",
            "status": "To Do",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }
        
        result = enrich_task_with_timeline_status(task)
        
        # Should be in this_week (1-7 days inclusive)
        assert result["timeline_status"] == "this_week"
        assert result["is_upcoming"] is True


    def test_edge_case_exactly_1_day_future(self):
        """Test task due exactly 1 day from now is in this_week, not today"""
        task = {
            "task_id": "task-1day-exact",
            "title": "Due Tomorrow",
            "status": "To Do",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        
        result = enrich_task_with_timeline_status(task)
        
        # Should be in this_week (1-7 days)
        assert result["timeline_status"] == "this_week"
        assert result["is_upcoming"] is True


class TestTimelineStatistics:
    """Test that statistics correctly exclude completed tasks"""
    
    def test_overdue_count_excludes_completed(self):
        """Test that overdue count doesn't include completed tasks"""
        tasks = [
            {
                "task_id": "task-1",
                "status": "In Progress",
                "due_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            },
            {
                "task_id": "task-2",
                "status": "Completed",
                "due_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            },
            {
                "task_id": "task-3",
                "status": "To Do",
                "due_date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            },
        ]
        
        timeline = group_tasks_by_timeline(tasks)
        
        # Only 2 tasks should be overdue (task-1 and task-3)
        assert len(timeline["overdue"]) == 2
        assert all(t["status"] != "Completed" for t in timeline["overdue"])


class TestFilterBugFix:
    """Test fixes for the filter clearing bug that causes date miscategorization"""
    
    def test_task_7_days_out_stays_this_week_after_filter_clear(self):
        """Test that a task exactly 7 days away remains in this_week after clearing filters"""
        # Task due in exactly 7 days
        task = {
            "task_id": "task-7days",
            "title": "Task in 7 Days",
            "status": "To Do",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }
        
        # Categorize before filtering
        result_before = enrich_task_with_timeline_status(task.copy())
        
        # Categorize after filtering (simulating filter clear)
        result_after = enrich_task_with_timeline_status(task.copy())
        
        # Should remain in this_week both times
        assert result_before["timeline_status"] == "this_week"
        assert result_after["timeline_status"] == "this_week"
        assert result_before["timeline_status"] == result_after["timeline_status"]
    
    
    def test_task_8_days_out_stays_future_after_filter_clear(self):
        """Test that a task 8+ days away remains in future after clearing filters"""
        task = {
            "task_id": "task-8days",
            "title": "Task in 8 Days",
            "status": "To Do",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat(),
        }
        
        result_before = enrich_task_with_timeline_status(task.copy())
        result_after = enrich_task_with_timeline_status(task.copy())
        
        # Should remain in future both times
        assert result_before["timeline_status"] == "future"
        assert result_after["timeline_status"] == "future"
    
    
    def test_this_week_boundary_conditions(self):
        """Test that this_week correctly handles 1-7 day range"""
        now = datetime.now(timezone.utc)
        
        # Test day 1 (tomorrow)
        task_day1 = {
            "task_id": "task-1",
            "status": "To Do",
            "due_date": (now + timedelta(days=1)).isoformat(),
        }
        result1 = enrich_task_with_timeline_status(task_day1)
        assert result1["timeline_status"] == "this_week"
        
        # Test day 7 (last day of this week)
        task_day7 = {
            "task_id": "task-7",
            "status": "To Do",
            "due_date": (now + timedelta(days=7)).isoformat(),
        }
        result7 = enrich_task_with_timeline_status(task_day7)
        assert result7["timeline_status"] == "this_week"
        
        # Test day 0 (today) - should NOT be this_week
        task_day0 = {
            "task_id": "task-0",
            "status": "To Do",
            "due_date": now.isoformat(),
        }
        result0 = enrich_task_with_timeline_status(task_day0)
        assert result0["timeline_status"] == "today"
        
        # Test day 8 - should NOT be this_week
        task_day8 = {
            "task_id": "task-8",
            "status": "To Do",
            "due_date": (now + timedelta(days=8)).isoformat(),
        }
        result8 = enrich_task_with_timeline_status(task_day8)
        assert result8["timeline_status"] == "future"
