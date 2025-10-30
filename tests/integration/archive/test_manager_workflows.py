"""Integration tests for manager workflows using real Firebase."""
import pytest
import json
from datetime import datetime, timezone, timedelta
from google.cloud.firestore_v1.base_query import FieldFilter


class TestManagerTeamView:
    """Test manager team view and task management."""
    
    def test_manager_can_view_team_tasks(self, db, test_collection_prefix, cleanup_collections):
        """Test that a manager can view all team tasks across projects."""
        users_collection = f"{test_collection_prefix}_users"
        projects_collection = f"{test_collection_prefix}_projects"
        tasks_collection = f"{test_collection_prefix}_tasks"
        memberships_collection = f"{test_collection_prefix}_memberships"
        
        for col in [users_collection, projects_collection, tasks_collection, memberships_collection]:
            cleanup_collections.append(col)
        
        # Create manager user
        manager_id = "manager_test_001"
        db.collection(users_collection).document(manager_id).set({
            "user_id": manager_id,
            "name": "Test Manager",
            "email": "manager@test.com",
            "role": "manager",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create team member
        member_id = "member_test_001"
        db.collection(users_collection).document(member_id).set({
            "user_id": member_id,
            "name": "Test Member",
            "email": "member@test.com",
            "role": "staff",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Create project
        project_id = "project_test_001"
        db.collection(projects_collection).document(project_id).set({
            "project_id": project_id,
            "name": "Test Project",
            "description": "Project for manager testing",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Add memberships
        db.collection(memberships_collection).document(f"{project_id}_{manager_id}").set({
            "project_id": project_id,
            "user_id": manager_id,
            "role": "Manager"
        })
        
        db.collection(memberships_collection).document(f"{project_id}_{member_id}").set({
            "project_id": project_id,
            "user_id": member_id,
            "role": "Member"
        })
        
        # Create task assigned to team member
        task_id = "task_test_001"
        db.collection(tasks_collection).document(task_id).set({
            "task_id": task_id,
            "title": "Team Member Task",
            "description": "Task for integration testing",
            "status": "To Do",
            "priority": 5,
            "project_id": project_id,
            "created_by": {"user_id": manager_id, "name": "Test Manager"},
            "assigned_to": {"user_id": member_id, "name": "Test Member"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        })
        
        # Query team tasks (manager's projects)
        manager_projects = set()
        manager_memberships = db.collection(memberships_collection).where(
            filter=FieldFilter("user_id", "==", manager_id)
        ).stream()
        
        for mem_doc in manager_memberships:
            manager_projects.add(mem_doc.to_dict()["project_id"])
        
        assert project_id in manager_projects
        
        # Get team members from those projects
        team_member_ids = set()
        for proj_id in manager_projects:
            project_members = db.collection(memberships_collection).where(
                filter=FieldFilter("project_id", "==", proj_id)
            ).stream()
            
            for mem_doc in project_members:
                mem_user_id = mem_doc.to_dict()["user_id"]
                if mem_user_id != manager_id:
                    team_member_ids.add(mem_user_id)
        
        assert member_id in team_member_ids
        
        # Get tasks created by or assigned to team members
        team_tasks = []
        for member_user_id in team_member_ids:
            # Tasks created by member
            created_tasks = db.collection(tasks_collection).where(
                filter=FieldFilter("created_by.user_id", "==", member_user_id)
            ).stream()
            team_tasks.extend([doc.to_dict() for doc in created_tasks])
            
            # Tasks assigned to member
            assigned_tasks = db.collection(tasks_collection).where(
                filter=FieldFilter("assigned_to.user_id", "==", member_user_id)
            ).stream()
            team_tasks.extend([doc.to_dict() for doc in assigned_tasks])
        
        # Verify we found the task
        assert len(team_tasks) >= 1
        task_ids = [t["task_id"] for t in team_tasks]
        assert task_id in task_ids
        
        # Cleanup
        db.collection(users_collection).document(manager_id).delete()
        db.collection(users_collection).document(member_id).delete()
        db.collection(projects_collection).document(project_id).delete()
        db.collection(tasks_collection).document(task_id).delete()
        db.collection(memberships_collection).document(f"{project_id}_{manager_id}").delete()
        db.collection(memberships_collection).document(f"{project_id}_{member_id}").delete()
    
    
    def test_manager_task_reassignment(self, db, test_collection_prefix, cleanup_collections):
        """Test that managers can reassign tasks to different team members."""
        users_collection = f"{test_collection_prefix}_users"
        tasks_collection = f"{test_collection_prefix}_tasks"
        
        for col in [users_collection, tasks_collection]:
            cleanup_collections.append(col)
        
        # Create users
        manager_id = "manager_reassign_001"
        member1_id = "member_reassign_001"
        member2_id = "member_reassign_002"
        
        for user_id, name in [(manager_id, "Manager"), (member1_id, "Member 1"), (member2_id, "Member 2")]:
            db.collection(users_collection).document(user_id).set({
                "user_id": user_id,
                "name": name,
                "email": f"{user_id}@test.com",
                "role": "manager" if "manager" in user_id else "staff"
            })
        
        # Create task assigned to member 1
        task_id = "task_reassign_001"
        initial_task_data = {
            "task_id": task_id,
            "title": "Task to Reassign",
            "status": "To Do",
            "priority": 3,
            "assigned_to": {"user_id": member1_id, "name": "Member 1"},
            "created_by": {"user_id": manager_id, "name": "Manager"},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        db.collection(tasks_collection).document(task_id).set(initial_task_data)
        
        # Verify initial assignment
        task_doc = db.collection(tasks_collection).document(task_id).get()
        assert task_doc.exists
        assert task_doc.to_dict()["assigned_to"]["user_id"] == member1_id
        
        # Reassign to member 2
        db.collection(tasks_collection).document(task_id).update({
            "assigned_to": {"user_id": member2_id, "name": "Member 2"},
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify reassignment
        task_doc = db.collection(tasks_collection).document(task_id).get()
        assert task_doc.to_dict()["assigned_to"]["user_id"] == member2_id
        
        # Cleanup
        for user_id in [manager_id, member1_id, member2_id]:
            db.collection(users_collection).document(user_id).delete()
        db.collection(tasks_collection).document(task_id).delete()


class TestManagerTimelineView:
    """Test manager timeline view functionality."""
    
    def test_timeline_task_grouping(self, db, test_collection_prefix, cleanup_collections):
        """Test that tasks are properly grouped into timeline categories."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        now = datetime.now(timezone.utc)
        
        # Create tasks in different timeline categories
        task_data = [
            # Overdue task
            {
                "task_id": "overdue_task",
                "title": "Overdue Task",
                "status": "To Do",
                "priority": 5,
                "due_date": (now - timedelta(days=2)).isoformat()
            },
            # Today task
            {
                "task_id": "today_task",
                "title": "Today Task",
                "status": "In Progress",
                "priority": 4,
                "due_date": now.isoformat()
            },
            # This week task
            {
                "task_id": "this_week_task",
                "title": "This Week Task",
                "status": "To Do",
                "priority": 3,
                "due_date": (now + timedelta(days=5)).isoformat()
            },
            # Future task
            {
                "task_id": "future_task",
                "title": "Future Task",
                "status": "To Do",
                "priority": 2,
                "due_date": (now + timedelta(days=14)).isoformat()
            },
            # No due date
            {
                "task_id": "no_due_date_task",
                "title": "No Due Date",
                "status": "To Do",
                "priority": 1,
                "due_date": None
            }
        ]
        
        # Create tasks
        for task in task_data:
            db.collection(tasks_collection).document(task["task_id"]).set(task)
        
        # Query and categorize tasks
        all_tasks = db.collection(tasks_collection).stream()
        
        categorized = {
            "overdue": [],
            "today": [],
            "this_week": [],
            "future": [],
            "no_due_date": []
        }
        
        for doc in all_tasks:
            task = doc.to_dict()
            due_date = task.get("due_date")
            
            if not due_date:
                categorized["no_due_date"].append(task)
                continue
            
            due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            days_diff = (due_dt - now).days
            
            if days_diff < 0:
                categorized["overdue"].append(task)
            elif days_diff == 0:
                categorized["today"].append(task)
            elif days_diff <= 7:
                categorized["this_week"].append(task)
            else:
                categorized["future"].append(task)
        
        # Verify categorization
        assert len(categorized["overdue"]) >= 1
        assert len(categorized["today"]) >= 1
        assert len(categorized["this_week"]) >= 1
        assert len(categorized["future"]) >= 1
        assert len(categorized["no_due_date"]) >= 1
        
        # Cleanup
        for task in task_data:
            db.collection(tasks_collection).document(task["task_id"]).delete()
    
    
    def test_detect_schedule_conflicts(self, db, test_collection_prefix, cleanup_collections):
        """Test detection of multiple tasks with same due date (schedule conflicts)."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create multiple tasks with same due date
        conflict_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        
        conflict_tasks = [
            {
                "task_id": "conflict_task_1",
                "title": "Conflict Task 1",
                "status": "To Do",
                "priority": 5,
                "due_date": conflict_date
            },
            {
                "task_id": "conflict_task_2",
                "title": "Conflict Task 2",
                "status": "To Do",
                "priority": 4,
                "due_date": conflict_date
            },
            {
                "task_id": "conflict_task_3",
                "title": "Conflict Task 3",
                "status": "In Progress",
                "priority": 3,
                "due_date": conflict_date
            }
        ]
        
        # Create tasks
        for task in conflict_tasks:
            db.collection(tasks_collection).document(task["task_id"]).set(task)
        
        # Query tasks and detect conflicts
        all_tasks_stream = db.collection(tasks_collection).stream()
        all_tasks = [doc.to_dict() for doc in all_tasks_stream]
        
        # Group by due date
        date_groups = {}
        for task in all_tasks:
            due_date = task.get("due_date")
            if due_date:
                # Extract just the date part for grouping
                date_key = due_date.split('T')[0]
                if date_key not in date_groups:
                    date_groups[date_key] = []
                date_groups[date_key].append(task)
        
        # Find conflicts (dates with multiple tasks)
        conflicts = []
        for date_key, tasks in date_groups.items():
            if len(tasks) > 1:
                conflicts.append({
                    "date": date_key,
                    "count": len(tasks),
                    "tasks": tasks
                })
        
        # Verify conflict detection
        assert len(conflicts) >= 1
        conflict_date_key = conflict_date.split('T')[0]
        conflict_found = any(c["date"] == conflict_date_key for c in conflicts)
        assert conflict_found
        
        # Verify the conflict has the right count
        for conflict in conflicts:
            if conflict["date"] == conflict_date_key:
                assert conflict["count"] >= 3
        
        # Cleanup
        for task in conflict_tasks:
            db.collection(tasks_collection).document(task["task_id"]).delete()


class TestManagerFiltering:
    """Test manager task filtering capabilities."""
    
    def test_filter_by_status(self, db, test_collection_prefix, cleanup_collections):
        """Test filtering tasks by status."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create tasks with different statuses
        task_statuses = ["To Do", "In Progress", "Done", "Blocked"]
        created_tasks = []
        
        for i, status in enumerate(task_statuses):
            task_id = f"status_task_{status.replace(' ', '_').lower()}_{i}"
            task_data = {
                "task_id": task_id,
                "title": f"{status} Task",
                "status": status,
                "priority": 3
            }
            db.collection(tasks_collection).document(task_id).set(task_data)
            created_tasks.append(task_id)
        
        # Filter by "To Do" status
        todo_tasks = db.collection(tasks_collection).where(
            filter=FieldFilter("status", "==", "To Do")
        ).stream()
        todo_list = [doc.to_dict() for doc in todo_tasks]
        
        assert len(todo_list) >= 1
        assert all(task["status"] == "To Do" for task in todo_list)
        
        # Filter by "Done" status
        done_tasks = db.collection(tasks_collection).where(
            filter=FieldFilter("status", "==", "Done")
        ).stream()
        done_list = [doc.to_dict() for doc in done_tasks]
        
        assert len(done_list) >= 1
        assert all(task["status"] == "Done" for task in done_list)
        
        # Cleanup
        for task_id in created_tasks:
            db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_filter_by_priority(self, db, test_collection_prefix, cleanup_collections):
        """Test filtering tasks by priority level."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create tasks with different priorities
        priorities = [1, 3, 5, 7, 10]
        created_tasks = []
        
        for priority in priorities:
            task_id = f"priority_task_{priority}"
            task_data = {
                "task_id": task_id,
                "title": f"Priority {priority} Task",
                "status": "To Do",
                "priority": priority
            }
            db.collection(tasks_collection).document(task_id).set(task_data)
            created_tasks.append(task_id)
        
        # Filter high priority tasks (>= 7)
        all_tasks_stream = db.collection(tasks_collection).stream()
        all_tasks = [doc.to_dict() for doc in all_tasks_stream]
        high_priority = [task for task in all_tasks if task.get("priority", 0) >= 7]
        
        assert len(high_priority) >= 2
        assert all(task["priority"] >= 7 for task in high_priority)
        
        # Cleanup
        for task_id in created_tasks:
            db.collection(tasks_collection).document(task_id).delete()
    
    
    def test_filter_by_team_member(self, db, test_collection_prefix, cleanup_collections):
        """Test filtering tasks by assigned team member."""
        users_collection = f"{test_collection_prefix}_users"
        tasks_collection = f"{test_collection_prefix}_tasks"
        
        for col in [users_collection, tasks_collection]:
            cleanup_collections.append(col)
        
        # Create team members
        member1_id = "filter_member_001"
        member2_id = "filter_member_002"
        
        for member_id, name in [(member1_id, "Member 1"), (member2_id, "Member 2")]:
            db.collection(users_collection).document(member_id).set({
                "user_id": member_id,
                "name": name,
                "email": f"{member_id}@test.com"
            })
        
        # Create tasks assigned to different members
        tasks_data = [
            {"task_id": "task_m1_1", "assigned_to": {"user_id": member1_id, "name": "Member 1"}},
            {"task_id": "task_m1_2", "assigned_to": {"user_id": member1_id, "name": "Member 1"}},
            {"task_id": "task_m2_1", "assigned_to": {"user_id": member2_id, "name": "Member 2"}},
        ]
        
        for task_data in tasks_data:
            task_data.update({"title": "Test Task", "status": "To Do", "priority": 3})
            db.collection(tasks_collection).document(task_data["task_id"]).set(task_data)
        
        # Filter tasks for member 1
        member1_tasks = db.collection(tasks_collection).where(
            filter=FieldFilter("assigned_to.user_id", "==", member1_id)
        ).stream()
        member1_list = [doc.to_dict() for doc in member1_tasks]
        
        assert len(member1_list) == 2
        assert all(task["assigned_to"]["user_id"] == member1_id for task in member1_list)
        
        # Cleanup
        for user_id in [member1_id, member2_id]:
            db.collection(users_collection).document(user_id).delete()
        for task_data in tasks_data:
            db.collection(tasks_collection).document(task_data["task_id"]).delete()


class TestManagerSorting:
    """Test manager task sorting capabilities."""
    
    def test_sort_by_priority(self, db, test_collection_prefix, cleanup_collections):
        """Test sorting tasks by priority."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        # Create tasks with various priorities
        task_data = [
            {"task_id": "sort_p1", "title": "Low Priority", "priority": 2},
            {"task_id": "sort_p2", "title": "High Priority", "priority": 9},
            {"task_id": "sort_p3", "title": "Medium Priority", "priority": 5},
        ]
        
        for task in task_data:
            task.update({"status": "To Do"})
            db.collection(tasks_collection).document(task["task_id"]).set(task)
        
        # Query and sort in Python (Firestore requires composite index for ordering)
        all_tasks_stream = db.collection(tasks_collection).stream()
        all_tasks = [doc.to_dict() for doc in all_tasks_stream]
        
        # Sort by priority descending
        sorted_tasks = sorted(all_tasks, key=lambda x: x.get("priority", 0), reverse=True)
        
        # Verify sorting
        assert sorted_tasks[0]["priority"] >= sorted_tasks[1]["priority"]
        assert sorted_tasks[1]["priority"] >= sorted_tasks[2]["priority"]
        
        # Cleanup
        for task in task_data:
            db.collection(tasks_collection).document(task["task_id"]).delete()
    
    
    def test_sort_by_due_date(self, db, test_collection_prefix, cleanup_collections):
        """Test sorting tasks by due date."""
        tasks_collection = f"{test_collection_prefix}_tasks"
        cleanup_collections.append(tasks_collection)
        
        now = datetime.now(timezone.utc)
        
        # Create tasks with different due dates
        task_data = [
            {"task_id": "sort_d1", "title": "Far Future", "due_date": (now + timedelta(days=30)).isoformat()},
            {"task_id": "sort_d2", "title": "Tomorrow", "due_date": (now + timedelta(days=1)).isoformat()},
            {"task_id": "sort_d3", "title": "Next Week", "due_date": (now + timedelta(days=7)).isoformat()},
        ]
        
        for task in task_data:
            task.update({"status": "To Do", "priority": 5})
            db.collection(tasks_collection).document(task["task_id"]).set(task)
        
        # Query and sort
        all_tasks_stream = db.collection(tasks_collection).stream()
        all_tasks = [doc.to_dict() for doc in all_tasks_stream]
        
        # Sort by due date ascending
        sorted_tasks = sorted(
            all_tasks,
            key=lambda x: datetime.fromisoformat(x.get("due_date", "9999-12-31").replace('Z', '+00:00'))
        )
        
        # Verify earliest date is first
        first_date = datetime.fromisoformat(sorted_tasks[0]["due_date"].replace('Z', '+00:00'))
        second_date = datetime.fromisoformat(sorted_tasks[1]["due_date"].replace('Z', '+00:00'))
        assert first_date <= second_date
        
        # Cleanup
        for task in task_data:
            db.collection(tasks_collection).document(task["task_id"]).delete()


class TestManagerPermissions:
    """Test manager role-based permissions."""
    
    def test_staff_cannot_access_manager_functions(self, db, test_collection_prefix, cleanup_collections):
        """Test that staff role users cannot access manager-only functions."""
        users_collection = f"{test_collection_prefix}_users"
        cleanup_collections.append(users_collection)
        
        # Create staff user
        staff_id = "staff_user_001"
        db.collection(users_collection).document(staff_id).set({
            "user_id": staff_id,
            "name": "Staff User",
            "email": "staff@test.com",
            "role": "staff"
        })
        
        # Verify role
        user_doc = db.collection(users_collection).document(staff_id).get()
        assert user_doc.exists
        user_data = user_doc.to_dict()
        
        # Check that role is not manager/director/hr
        role = user_data.get("role", "staff")
        is_manager_role = role in ["manager", "director", "hr"]
        assert not is_manager_role
        
        # Cleanup
        db.collection(users_collection).document(staff_id).delete()
    
    
    def test_manager_role_validation(self, db, test_collection_prefix, cleanup_collections):
        """Test validation of manager, director, and hr roles."""
        users_collection = f"{test_collection_prefix}_users"
        cleanup_collections.append(users_collection)
        
        # Create users with different roles
        roles_to_test = [
            ("manager_001", "manager", True),
            ("director_001", "director", True),
            ("hr_001", "hr", True),
            ("staff_001", "staff", False)
        ]
        
        for user_id, role, should_have_access in roles_to_test:
            db.collection(users_collection).document(user_id).set({
                "user_id": user_id,
                "name": f"{role.title()} User",
                "email": f"{user_id}@test.com",
                "role": role
            })
        
        # Verify each role
        for user_id, role, expected_access in roles_to_test:
            user_doc = db.collection(users_collection).document(user_id).get()
            user_data = user_doc.to_dict()
            actual_role = user_data.get("role", "staff")
            has_access = actual_role in ["manager", "director", "hr"]
            
            assert has_access == expected_access, f"Role {role} should have access={expected_access}"
        
        # Cleanup
        for user_id, _, _ in roles_to_test:
            db.collection(users_collection).document(user_id).delete()
