from datetime import datetime, timezone
from flask import request, jsonify
from . import manager_bp
from firebase_admin import firestore

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def _get_viewer_id():
    """Extract current user ID from request headers or query params."""
    viewer_id = (request.headers.get("X-User-Id") or request.args.get("viewer_id") or "").strip()
    return viewer_id

def _safe_iso_to_dt(s):
    """Safely convert ISO string to datetime object."""
    try:
        if not s:
            return None
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        # Ensure the datetime is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _is_manager_role(role):
    """Check if role is manager or above."""
    manager_roles = ["manager", "director", "hr"]
    return role in manager_roles

def _get_task_status_flags(due_date_str):
    """Calculate overdue/upcoming status for a task with visual categorization."""
    if not due_date_str:
        return {
            "is_overdue": False, 
            "is_upcoming": False, 
            "status": "no_due_date",
            "visual_status": "no_due_date",
            "days_overdue": 0,
            "days_until_due": None
        }
    
    due_dt = _safe_iso_to_dt(due_date_str)
    if not due_dt:
        return {
            "is_overdue": False, 
            "is_upcoming": False, 
            "status": "invalid_date",
            "visual_status": "invalid_date",
            "days_overdue": 0,
            "days_until_due": None
        }
    
    now = datetime.now(timezone.utc)
    days_until_due = (due_dt - now).days
    
    if days_until_due < -7:
        return {
            "is_overdue": True, 
            "is_upcoming": False, 
            "status": "critical_overdue",
            "visual_status": "critical_overdue",
            "days_overdue": abs(days_until_due),
            "days_until_due": days_until_due
        }
    elif days_until_due < 0:
        return {
            "is_overdue": True, 
            "is_upcoming": False, 
            "status": "overdue",
            "visual_status": "overdue",
            "days_overdue": abs(days_until_due),
            "days_until_due": days_until_due
        }
    elif days_until_due <= 3:
        return {
            "is_upcoming": True, 
            "is_overdue": False, 
            "status": "upcoming",
            "visual_status": "upcoming",
            "days_overdue": 0,
            "days_until_due": days_until_due
        }
    else:
        return {
            "is_overdue": False, 
            "is_upcoming": False, 
            "status": "on_track",
            "visual_status": "on_track",
            "days_overdue": 0,
            "days_until_due": days_until_due
        }

def _enrich_task_with_status(task_data, task_id):
    """Enrich task data with status flags and member info."""
    enriched = {
        "task_id": task_id,
        "title": task_data.get("title"),
        "description": task_data.get("description"),
        "priority": task_data.get("priority", 5),
        "status": task_data.get("status", "To Do"),
        "due_date": task_data.get("due_date"),
        "created_at": task_data.get("created_at"),
        "updated_at": task_data.get("updated_at"),
        "created_by": task_data.get("created_by"),
        "assigned_to": task_data.get("assigned_to"),
        "project_id": task_data.get("project_id"),
        "labels": task_data.get("labels", []),
    }
    
    # Add status flags
    status_flags = _get_task_status_flags(task_data.get("due_date"))
    enriched.update(status_flags)
    
    return enriched

def _group_tasks_by_timeline(tasks):
    """Group tasks by timeline periods (reused from dashboard.py logic)."""
    timeline = {
        "overdue": [],
        "today": [],
        "this_week": [],
        "future": [],
        "no_due_date": []
    }
    
    for task in tasks:
        due_date = task.get("due_date")
        if not due_date:
            timeline["no_due_date"].append(task)
            continue
        
        due_dt = _safe_iso_to_dt(due_date)
        if not due_dt:
            timeline["no_due_date"].append(task)
            continue
        
        now = datetime.now(timezone.utc)
        days_until_due = (due_dt - now).days
        
        if days_until_due < 0:
            timeline["overdue"].append(task)
        elif days_until_due == 0:
            timeline["today"].append(task)
        elif days_until_due <= 7:
            timeline["this_week"].append(task)
        else:
            timeline["future"].append(task)
    
    return timeline

def _detect_conflicts(tasks):
    """Detect tasks with overlapping due dates (reused from dashboard.py logic)."""
    date_map = {}
    conflicts = []
    
    for task in tasks:
        due_date = task.get("due_date")
        if due_date:
            date_str = due_date.split('T')[0]  # Extract just the date part
            if date_str not in date_map:
                date_map[date_str] = []
            date_map[date_str].append(task)
    
    # Find dates with multiple tasks
    for date_str, tasks_on_date in date_map.items():
        if len(tasks_on_date) > 1:
            conflicts.append({
                "date": date_str,
                "tasks": tasks_on_date,
                "count": len(tasks_on_date)
            })
    
    return conflicts

@manager_bp.get("/team-tasks")
def get_team_tasks():
    """Get all team members' tasks for a manager."""
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "manager_id required via X-User-Id header or ?viewer_id"}), 401
    
    # Verify manager exists and has manager+ role
    manager_doc = db.collection("users").document(manager_id).get()
    if not manager_doc.exists:
        return jsonify({"error": "Manager not found"}), 404
    
    manager_data = manager_doc.to_dict()
    manager_role = manager_data.get("role", "staff")
    
    if not _is_manager_role(manager_role):
        return jsonify({"error": "Only managers and above can access team tasks"}), 403
    
    # Get query parameters
    sort_by = request.args.get("sort_by", "due_date")
    sort_order = request.args.get("sort_order", "asc")
    filter_by = request.args.get("filter_by", "")
    filter_value = request.args.get("filter_value", "")
    view_mode = request.args.get("view_mode", "grid")
    
    # Find all projects where manager is a member
    manager_memberships = db.collection("memberships").where("user_id", "==", manager_id).stream()
    manager_projects = set()
    for mem in manager_memberships:
        manager_projects.add(mem.to_dict().get("project_id"))
    
    if not manager_projects:
        return jsonify({
            "team_tasks": [],
            "team_members": [],
            "projects": [],
            "statistics": {
                "total_tasks": 0,
                "overdue_count": 0,
                "upcoming_count": 0,
                "by_status": {},
                "by_priority": {}
            }
        }), 200
    
    # Get all members from those projects (excluding the manager)
    team_member_ids = set()
    project_memberships = {}
    
    for project_id in manager_projects:
        project_members = db.collection("memberships").where("project_id", "==", project_id).stream()
        project_member_ids = []
        for mem in project_members:
            user_id = mem.to_dict().get("user_id")
            if user_id != manager_id:  # Exclude manager
                team_member_ids.add(user_id)
                project_member_ids.append(user_id)
        project_memberships[project_id] = project_member_ids
    
    # Get all tasks for team members
    all_tasks = []
    for member_id in team_member_ids:
        # Get tasks created by this member
        created_tasks = db.collection("tasks").where("created_by.user_id", "==", member_id).stream()
        for task_doc in created_tasks:
            task_data = task_doc.to_dict()
            enriched_task = _enrich_task_with_status(task_data, task_doc.id)
            enriched_task["member_id"] = member_id
            enriched_task["member_role"] = "creator"
            all_tasks.append(enriched_task)
        
        # Get tasks assigned to this member
        assigned_tasks = db.collection("tasks").where("assigned_to.user_id", "==", member_id).stream()
        for task_doc in assigned_tasks:
            task_data = task_doc.to_dict()
            enriched_task = _enrich_task_with_status(task_data, task_doc.id)
            enriched_task["member_id"] = member_id
            enriched_task["member_role"] = "assignee"
            all_tasks.append(enriched_task)
    
    # Remove duplicates (task might be both created by and assigned to same person)
    seen_tasks = set()
    unique_tasks = []
    for task in all_tasks:
        task_key = task["task_id"]
        if task_key not in seen_tasks:
            seen_tasks.add(task_key)
            unique_tasks.append(task)
    
    # Apply filtering if specified
    if filter_by and filter_value:
        if filter_by == "member":
            unique_tasks = [t for t in unique_tasks if t.get("member_id") == filter_value]
        elif filter_by == "project":
            unique_tasks = [t for t in unique_tasks if t.get("project_id") == filter_value]
        elif filter_by == "status":
            unique_tasks = [t for t in unique_tasks if t.get("status") == filter_value]
        elif filter_by == "visual_status":
            unique_tasks = [t for t in unique_tasks if t.get("visual_status") == filter_value]
    
    # Sort tasks
    if sort_by == "due_date":
        unique_tasks.sort(key=lambda t: _safe_iso_to_dt(t.get("due_date")) or datetime.max.replace(tzinfo=timezone.utc), reverse=(sort_order == "desc"))
    elif sort_by == "priority":
        unique_tasks.sort(key=lambda t: t.get("priority", 5), reverse=(sort_order == "desc"))
    elif sort_by == "project":
        unique_tasks.sort(key=lambda t: t.get("project_id") or "", reverse=(sort_order == "desc"))
    
    # Get team member details
    team_members = []
    for member_id in team_member_ids:
        member_doc = db.collection("users").document(member_id).get()
        if member_doc.exists:
            member_data = member_doc.to_dict()
            team_members.append({
                "user_id": member_id,
                "name": member_data.get("name"),
                "email": member_data.get("email"),
                "role": member_data.get("role", "staff")
            })
    
    # Get project details
    projects = []
    for project_id in manager_projects:
        project_doc = db.collection("projects").document(project_id).get()
        if project_doc.exists:
            project_data = project_doc.to_dict()
            projects.append({
                "project_id": project_id,
                "name": project_data.get("name"),
                "description": project_data.get("description"),
                "member_count": len(project_memberships.get(project_id, []))
            })
    
    # Calculate statistics
    overdue_count = sum(1 for t in unique_tasks if t.get("is_overdue"))
    upcoming_count = sum(1 for t in unique_tasks if t.get("is_upcoming"))
    critical_overdue_count = sum(1 for t in unique_tasks if t.get("visual_status") == "critical_overdue")
    
    status_breakdown = {}
    priority_breakdown = {}
    visual_status_breakdown = {}
    for task in unique_tasks:
        status = task.get("status", "To Do")
        priority = task.get("priority", 5)
        visual_status = task.get("visual_status", "no_due_date")
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
        priority_breakdown[f"Priority {priority}"] = priority_breakdown.get(f"Priority {priority}", 0) + 1
        visual_status_breakdown[visual_status] = visual_status_breakdown.get(visual_status, 0) + 1
    
    response_data = {
        "team_tasks": unique_tasks,
        "team_members": team_members,
        "projects": projects,
        "statistics": {
            "total_tasks": len(unique_tasks),
            "overdue_count": overdue_count,
            "upcoming_count": upcoming_count,
            "critical_overdue_count": critical_overdue_count,
            "by_status": status_breakdown,
            "by_priority": priority_breakdown,
            "by_visual_status": visual_status_breakdown
        }
    }
    
    # Add timeline data if requested
    if view_mode == "timeline":
        timeline_data = _group_tasks_by_timeline(unique_tasks)
        conflicts = _detect_conflicts(unique_tasks)
        
        response_data["timeline"] = timeline_data
        response_data["conflicts"] = conflicts
        response_data["timeline_statistics"] = {
            "total_tasks": len(unique_tasks),
            "overdue_count": len(timeline_data["overdue"]),
            "today_count": len(timeline_data["today"]),
            "this_week_count": len(timeline_data["this_week"]),
            "future_count": len(timeline_data["future"]),
            "no_due_date_count": len(timeline_data["no_due_date"]),
            "conflict_count": len(conflicts)
        }
    
    return jsonify(response_data), 200
