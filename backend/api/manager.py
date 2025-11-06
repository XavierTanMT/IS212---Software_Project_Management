# filepath: /Users/xaviertan/Documents/GitHub/IS212---Software_Project_Management/backend/api/manager.py

from datetime import datetime, timezone
from flask import request, jsonify
from . import manager_bp
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

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
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _is_manager_role(role):
    """Check if role is manager or above."""
    manager_roles = ["manager", "director", "hr", "admin"]
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
    
    status_flags = _get_task_status_flags(task_data.get("due_date"))
    enriched.update(status_flags)
    
    return enriched

def _group_tasks_by_timeline(tasks):
    """Group tasks by timeline periods."""
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
    """Detect tasks with overlapping due dates."""
    date_map = {}
    conflicts = []
    
    for task in tasks:
        due_date = task.get("due_date")
        if due_date:
            date_str = due_date.split('T')[0]
            if date_str not in date_map:
                date_map[date_str] = []
            date_map[date_str].append(task)
    
    for date_str, tasks_on_date in date_map.items():
        if len(tasks_on_date) > 1:
            conflicts.append({
                "date": date_str,
                "tasks": tasks_on_date,
                "count": len(tasks_on_date)
            })
    
    return conflicts

def _verify_manager_access(manager_id):
    """Verify manager exists and has appropriate role."""
    db = firestore.client()
    manager_doc = db.collection("users").document(manager_id).get()
    
    if not manager_doc.exists:
        return None, jsonify({"error": "Manager not found"}), 404
    
    manager_data = manager_doc.to_dict()
    manager_role = manager_data.get("role", "staff")
    
    if not _is_manager_role(manager_role):
        return None, jsonify({"error": "Only managers and above can access this endpoint"}), 403
    
    return manager_data, None, None

def _get_manager_team_member_ids(manager_id):
    """Get all team member IDs for a manager."""
    db = firestore.client()
    
    # Get manager's projects
    manager_memberships = db.collection("memberships").where("user_id", "==", manager_id).stream()
    manager_projects = set(mem.to_dict().get("project_id") for mem in manager_memberships)
    
    if not manager_projects:
        return set()
    
    # Get all team members from those projects
    team_member_ids = set()
    for project_id in manager_projects:
        project_members = db.collection("memberships").where("project_id", "==", project_id).stream()
        for mem in project_members:
            user_id = mem.to_dict().get("user_id")
            if user_id != manager_id:  # Exclude manager
                team_member_ids.add(user_id)
    
    return team_member_ids

@manager_bp.get("/dashboard")
def manager_dashboard():
    """
    GET /api/manager/dashboard
    
    Manager's main dashboard with team overview, statistics, and recent activity.
    
    Headers:
        X-User-Id: Manager's user ID
    
    Returns:
        {
            "view": "manager",
            "manager": {...},
            "team_size": 5,
            "active_tasks": 10,
            "completed_tasks": 3,
            "team_members": [...],
            "team_tasks": [...],
            "statistics": {...}
        }
    """
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "Manager ID required via X-User-Id header"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    # Get manager's projects
    manager_memberships = db.collection("memberships").where("user_id", "==", manager_id).stream()
    manager_projects = set()
    for mem in manager_memberships:
        manager_projects.add(mem.to_dict().get("project_id"))
    
    # Get team member IDs
    team_member_ids = _get_manager_team_member_ids(manager_id)

    # Fallback: If no memberships found, also consider users who have manager_id set
    if not team_member_ids:
        try:
            users_q = db.collection("users").where(filter=FieldFilter("manager_id", "==", manager_id)).stream()
            for udoc in users_q:
                uid = udoc.id
                if uid != manager_id:
                    team_member_ids.add(uid)
        except Exception:
            # Ignore fallback errors and continue with whatever we have
            pass
    
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
                "role": member_data.get("role", "staff"),
                "is_active": member_data.get("is_active", True)
            })
    
    # Get all team tasks
    all_tasks = []
    active_tasks = 0
    completed_tasks = 0
    overdue_tasks = 0
    
    for member_id in team_member_ids:
        # Created tasks
        created_tasks = db.collection("tasks").where("created_by.user_id", "==", member_id).stream()
        for task_doc in created_tasks:
            task_data = task_doc.to_dict()
            enriched_task = _enrich_task_with_status(task_data, task_doc.id)
            
            # Count by status
            status = task_data.get("status", "To Do")
            if status in ["To Do", "In Progress"]:
                active_tasks += 1
            elif status == "Completed":
                completed_tasks += 1
            
            if enriched_task.get("is_overdue"):
                overdue_tasks += 1
            
            all_tasks.append(enriched_task)
        
        # Assigned tasks
        assigned_tasks = db.collection("tasks").where("assigned_to.user_id", "==", member_id).stream()
        for task_doc in assigned_tasks:
            task_data = task_doc.to_dict()
            enriched_task = _enrich_task_with_status(task_data, task_doc.id)
            
            status = task_data.get("status", "To Do")
            if status in ["To Do", "In Progress"]:
                active_tasks += 1
            elif status == "Completed":
                completed_tasks += 1
            
            if enriched_task.get("is_overdue"):
                overdue_tasks += 1
            
            all_tasks.append(enriched_task)
    
    # Remove duplicate tasks
    seen_tasks = set()
    unique_tasks = []
    for task in all_tasks:
        task_key = task["task_id"]
        if task_key not in seen_tasks:
            seen_tasks.add(task_key)
            unique_tasks.append(task)
    
    # Sort by due date (most urgent first)
    unique_tasks.sort(
        key=lambda t: _safe_iso_to_dt(t.get("due_date")) or datetime.max.replace(tzinfo=timezone.utc)
    )
    
    # Get recent tasks (last 10)
    recent_tasks = unique_tasks[:10]
    
    # Calculate statistics
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
    
    return jsonify({
        "view": "manager",
        "manager": {
            "user_id": manager_id,
            "name": manager_data.get("name"),
            "email": manager_data.get("email"),
            "role": manager_data.get("role", "manager")
        },
        "team_size": len(team_members),
        "active_tasks": active_tasks,
        "completed_tasks": completed_tasks,
        "total_tasks": len(unique_tasks),
        "overdue_tasks": overdue_tasks,
        "team_members": team_members,
        "team_tasks": recent_tasks,  # Recent 10 tasks
        "statistics": {
            "total_tasks": len(unique_tasks),
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "overdue_count": overdue_tasks,
            "by_status": status_breakdown,
            "by_priority": priority_breakdown,
            "by_visual_status": visual_status_breakdown
        }
    }), 200

# ========== EXISTING ENDPOINT (Keep as is) ==========
@manager_bp.get("/team-tasks")
def get_team_tasks():
    """Get all team members' tasks for a manager."""
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "manager_id required via X-User-Id header or ?viewer_id"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    # Get query parameters
    sort_by = request.args.get("sort_by", "due_date")
    sort_order = request.args.get("sort_order", "asc")
    filter_by = request.args.get("filter_by", "")
    filter_value = request.args.get("filter_value", "")
    view_mode = request.args.get("view_mode", "grid")
    
    # Find all projects where manager is a member
    manager_memberships = db.collection("memberships").where(filter=FieldFilter("user_id", "==", manager_id)).stream()
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
    
    # Get all members from those projects
    team_member_ids = set()
    project_memberships = {}
    
    for project_id in manager_projects:
        project_members = db.collection("memberships").where(filter=FieldFilter("project_id", "==", project_id)).stream()
        project_member_ids = []
        for mem in project_members:
            user_id = mem.to_dict().get("user_id")
            if user_id != manager_id:
                team_member_ids.add(user_id)
                project_member_ids.append(user_id)
        project_memberships[project_id] = project_member_ids
    
    # Get all tasks for team members
    all_tasks = []
    for member_id in team_member_ids:
        # Get tasks created by this member
        created_tasks = db.collection("tasks").where(filter=FieldFilter("created_by.user_id", "==", member_id)).stream()
        for task_doc in created_tasks:
            task_data = task_doc.to_dict()
            enriched_task = _enrich_task_with_status(task_data, task_doc.id)
            enriched_task["member_id"] = member_id
            enriched_task["member_role"] = "creator"
            all_tasks.append(enriched_task)
        
        # Get tasks assigned to this member
        assigned_tasks = db.collection("tasks").where(filter=FieldFilter("assigned_to.user_id", "==", member_id)).stream()
        for task_doc in assigned_tasks:
            task_data = task_doc.to_dict()
            enriched_task = _enrich_task_with_status(task_data, task_doc.id)
            enriched_task["member_id"] = member_id
            enriched_task["member_role"] = "assignee"
            all_tasks.append(enriched_task)
    
    # Remove duplicates
    seen_tasks = set()
    unique_tasks = []
    for task in all_tasks:
        task_key = task["task_id"]
        if task_key not in seen_tasks:
            seen_tasks.add(task_key)
            unique_tasks.append(task)
    
    # Apply filtering
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
    sort_functions = {
        "due_date": lambda t: _safe_iso_to_dt(t.get("due_date")) or datetime.max.replace(tzinfo=timezone.utc),
        "priority": lambda t: t.get("priority", 5),
        "project": lambda t: t.get("project_id") or "",
    }
    if sort_by in sort_functions:
        unique_tasks.sort(key=sort_functions[sort_by], reverse=(sort_order == "desc"))
    
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

# ========== NEW ENDPOINTS (Add these) ==========

@manager_bp.post("/tasks/<task_id>/assign")
def assign_task(task_id):
    """
    Assign task to team member(s) - Manager.assignTask() from diagram.
    Accept team members from projects AND direct manager-staff relationship.
    """
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "manager_id required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json() or {}
    assignee_ids = data.get("assignee_ids", [])
    
    if not assignee_ids or not isinstance(assignee_ids, list):
        return jsonify({"error": "assignee_ids required"}), 400
    
    # Get task
    task_ref = db.collection("tasks").document(task_id)
    task_doc = task_ref.get()
    
    if not task_doc.exists:
        return jsonify({"error": "Task not found"}), 404
    
    # Get team members from BOTH sources
    # Method 1: Existing project-based team members
    project_team_ids = _get_manager_team_member_ids(manager_id)  # returns set()
    
    # Method 2: Direct manager->staff relationship (users where manager_id == manager_id)
    direct_staff_query = db.collection("users").where("manager_id", "==", manager_id).stream()
    direct_staff_ids = set(doc.id for doc in direct_staff_query)
    
    # Combine both sources
    all_team_member_ids = set(project_team_ids) | direct_staff_ids
    
    # Verify assignees are in the combined team
    for assignee_id in assignee_ids:
        if assignee_id not in all_team_member_ids:
            return jsonify({"error": f"User {assignee_id} is not in your team"}), 403
    
    # Get assignee details
    assigned_to_list = []
    for assignee_id in assignee_ids:
        user_doc = db.collection("users").document(assignee_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            assigned_to_list.append({
                "user_id": assignee_id,
                "name": user_data.get("name"),
                "email": user_data.get("email")
            })
    
    # Update task
    task_ref.update({
        "assigned_to": assigned_to_list[0] if len(assigned_to_list) == 1 else assigned_to_list,
        "updated_at": now_iso(),
        "updated_by": {
            "user_id": manager_id,
            "name": manager_data.get("name"),
            "email": manager_data.get("email")
        }
    })
    
    return jsonify({
        "success": True,
        "message": f"Task assigned to {len(assignee_ids)} member(s)",
        "task_id": task_id,
        "assigned_to": assigned_to_list[0] if len(assigned_to_list) == 1 else assigned_to_list
    }), 200

@manager_bp.post("/projects")
def create_project():
    """Create new project - Manager.createProject() from diagram."""
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "manager_id required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    
    project_data = {
        "name": data.get("name"),
        "description": data.get("description", ""),
        "created_by": {
            "user_id": manager_id,
            "name": manager_data.get("name"),
            "email": manager_data.get("email")
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "active"
    }
    
    # Create project
    project_ref = db.collection("projects").add(project_data)
    project_id = project_ref[1].id
    
    # Add manager as first project member
    db.collection("memberships").add({
        "project_id": project_id,
        "user_id": manager_id,
        "role": "manager",
        "joined_at": now_iso()
    })
    
    return jsonify({
        "success": True,
        "message": "Project created successfully",
        "project_id": project_id,
        "project": {
            "project_id": project_id,
            **project_data
        }
    }), 201

@manager_bp.post("/projects/<project_id>/members")
def add_team_member(project_id):
    """Add member to project."""
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "manager_id required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    user_id = data.get("user_id")
    
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    
    # Verify project exists
    project_doc = db.collection("projects").document(project_id).get()
    if not project_doc.exists:
        return jsonify({"error": "Project not found"}), 404
    
    # Verify user exists
    user_doc = db.collection("users").document(user_id).get()
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404
    
    # Check if already a member
    existing = db.collection("memberships")\
        .where("project_id", "==", project_id)\
        .where("user_id", "==", user_id)\
        .limit(1).get()
    
    if existing:
        return jsonify({"error": "User is already a project member"}), 400
    
    # Add membership
    db.collection("memberships").add({
        "project_id": project_id,
        "user_id": user_id,
        "role": "member",
        "joined_at": now_iso(),
        "added_by": manager_id
    })
    
    return jsonify({
        "success": True,
        "message": "Member added to project"
    }), 201

# Add after line 717, before the manager-staff relationship endpoints

@manager_bp.get("/all-users")
def get_all_users():
    """
    GET /api/manager/all-users
    
    Get all users (staff and managers) for assignment purposes.
    Managers can see all users to assign staff to themselves or other managers.
    
    Headers:
        X-User-Id: Manager's user ID
    
    Returns:
        {
            "staff": [...],
            "managers": [...],
            "total_staff": 5,
            "total_managers": 3
        }
    """
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "Manager ID required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    try:
        # Get all users
        users_ref = db.collection("users")
        all_users = users_ref.stream()
        
        staff_list = []
        manager_list = []
        
        for user_doc in all_users:
            user_data = user_doc.to_dict()
            user_role = user_data.get("role", "staff")
            
            user_info = {
                "user_id": user_doc.id,
                "name": user_data.get("name"),
                "email": user_data.get("email"),
                "role": user_role,
                "is_active": user_data.get("is_active", True),
                "manager_id": user_data.get("manager_id"),
                "created_at": user_data.get("created_at")
            }
            
            if user_role == "staff":
                staff_list.append(user_info)
            elif user_role in ["manager", "director", "hr", "admin"]:
                manager_list.append(user_info)
        
        return jsonify({
            "staff": staff_list,
            "managers": manager_list,
            "total_staff": len(staff_list),
            "total_managers": len(manager_list)
        }), 200
        
    except Exception as e:
        print(f"Error getting all users: {e}")
        return jsonify({"error": str(e)}), 500


@manager_bp.delete("/projects/<project_id>/members/<user_id>")
def remove_team_member(project_id, user_id):
    """Remove member from project."""
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "manager_id required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    # Find membership
    memberships = db.collection("memberships")\
        .where("project_id", "==", project_id)\
        .where("user_id", "==", user_id)\
        .limit(1).get()
    
    if not memberships:
        return jsonify({"error": "Membership not found"}), 404
    
    # Delete membership
    for membership in memberships:
        membership.reference.delete()
    
    return jsonify({
        "success": True,
        "message": "Member removed from project"
    }), 200

@manager_bp.get("/team-members/<member_id>")
def get_team_member_overview(member_id):
    """Get specific team member's task overview."""
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "manager_id required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    # Verify member is in team
    team_member_ids = _get_manager_team_member_ids(manager_id)
    if member_id not in team_member_ids:
        return jsonify({"error": "User is not in your team"}), 403
    
    # Get member details
    member_doc = db.collection("users").document(member_id).get()
    if not member_doc.exists:
        return jsonify({"error": "Member not found"}), 404
    
    member_data = member_doc.to_dict()
    
    # Get member's tasks
    created_tasks = db.collection("tasks").where("created_by.user_id", "==", member_id).stream()
    assigned_tasks = db.collection("tasks").where("assigned_to.user_id", "==", member_id).stream()
    
    all_tasks = []
    for task_doc in created_tasks:
        task_data = task_doc.to_dict()
        enriched = _enrich_task_with_status(task_data, task_doc.id)
        enriched["task_type"] = "created"
        all_tasks.append(enriched)
    
    for task_doc in assigned_tasks:
        task_data = task_doc.to_dict()
        enriched = _enrich_task_with_status(task_data, task_doc.id)
        enriched["task_type"] = "assigned"
        all_tasks.append(enriched)
    
    # Calculate statistics
    overdue = sum(1 for t in all_tasks if t.get("is_overdue"))
    upcoming = sum(1 for t in all_tasks if t.get("is_upcoming"))
    
    status_breakdown = {}
    for task in all_tasks:
        status = task.get("status", "To Do")
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
    
    return jsonify({
        "member": {
            "user_id": member_id,
            "name": member_data.get("name"),
            "email": member_data.get("email"),
            "role": member_data.get("role")
        },
        "tasks": all_tasks,
        "statistics": {
            "total_tasks": len(all_tasks),
            "overdue_count": overdue,
            "upcoming_count": upcoming,
            "by_status": status_breakdown
        }
    }), 200

@manager_bp.put("/tasks/<task_id>/status")
def update_task_status(task_id):
    """Update task status - uses Task.setStatus() from diagram."""
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "manager_id required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    new_status = data.get("status")
    
    valid_statuses = ["To Do", "In Progress", "Completed", "Blocked"]
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {valid_statuses}"}), 400
    
    # Get task
    task_ref = db.collection("tasks").document(task_id)
    task_doc = task_ref.get()
    
    if not task_doc.exists:
        return jsonify({"error": "Task not found"}), 404
    
    # Verify task belongs to team
    task_data = task_doc.to_dict()
    creator_id = task_data.get("created_by", {}).get("user_id")
    team_member_ids = _get_manager_team_member_ids(manager_id)
    
    if creator_id not in team_member_ids:
        return jsonify({"error": "Task does not belong to your team"}), 403
    
    # Update status
    task_ref.update({
        "status": new_status,
        "updated_at": now_iso(),
        "updated_by": {
            "user_id": manager_id,
            "name": manager_data.get("name")
        }
    })
    
    return jsonify({
        "success": True,
        "message": "Task status updated",
        "task_id": task_id,
        "new_status": new_status
    }), 200

@manager_bp.put("/tasks/<task_id>/priority")
def update_task_priority(task_id):
    """Update task priority - uses Task.setPriority() from diagram."""
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "manager_id required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    new_priority = data.get("priority")
    
    if not isinstance(new_priority, int) or new_priority < 1 or new_priority > 10:
        return jsonify({"error": "Priority must be an integer between 1 and 10"}), 400
    
    # Get task
    task_ref = db.collection("tasks").document(task_id)
    task_doc = task_ref.get()
    
    if not task_doc.exists:
        return jsonify({"error": "Task not found"}), 404
    
    # Verify task belongs to team
    task_data = task_doc.to_dict()
    creator_id = task_data.get("created_by", {}).get("user_id")
    team_member_ids = _get_manager_team_member_ids(manager_id)
    
    if creator_id not in team_member_ids:
        return jsonify({"error": "Task does not belong to your team"}), 403
    
    # Update priority
    task_ref.update({
        "priority": new_priority,
        "updated_at": now_iso(),
        "updated_by": {
            "user_id": manager_id,
            "name": manager_data.get("name")
        }
    })
    
    return jsonify({
        "success": True,
        "message": "Task priority updated",
        "task_id": task_id,
        "new_priority": new_priority
    }), 200


# Add these endpoints after your existing endpoints (around line 718)

# ========== MANAGER-STAFF RELATIONSHIP ENDPOINTS ==========

@manager_bp.post("/staff/<staff_id>/assign-manager")
def assign_manager_to_staff(staff_id):
    """
    POST /api/manager/staff/<staff_id>/assign-manager
    
    Assign a manager ID to a staff member's document.
    
    Headers:
        X-User-Id: Manager's user ID (the manager assigning themselves)
    
    Body:
        {
            "manager_id": "mgr123"  // Optional, defaults to X-User-Id
        }
    
    Returns:
        {
            "success": true,
            "message": "Manager assigned to staff member",
            "staff_id": "staff123",
            "manager_id": "mgr123"
        }
    """
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "Manager ID required via X-User-Id header"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    # Get optional manager_id from body (defaults to current manager)
    data = request.get_json() or {}
    target_manager_id = data.get("manager_id", manager_id)
    
    # Verify target manager exists and has manager role
    target_manager_doc = db.collection("users").document(target_manager_id).get()
    if not target_manager_doc.exists:
        return jsonify({"error": "Target manager not found"}), 404
    
    target_manager_data = target_manager_doc.to_dict()
    if not _is_manager_role(target_manager_data.get("role", "staff")):
        return jsonify({"error": "Target user is not a manager"}), 400
    
    # Verify staff exists
    staff_ref = db.collection("users").document(staff_id)
    staff_doc = staff_ref.get()
    
    if not staff_doc.exists:
        return jsonify({"error": "Staff member not found"}), 404
    
    staff_data = staff_doc.to_dict()
    
    # Verify staff is actually staff role
    if staff_data.get("role") != "staff":
        return jsonify({"error": "User is not a staff member"}), 400
    
    # Update staff document with manager_id
    staff_ref.update({
        "manager_id": target_manager_id,
        "manager_name": target_manager_data.get("name"),
        "manager_email": target_manager_data.get("email"),
        "manager_assigned_at": now_iso(),
        "updated_at": now_iso()
    })
    
    return jsonify({
        "success": True,
        "message": "Manager assigned to staff member",
        "staff_id": staff_id,
        "staff_name": staff_data.get("name"),
        "manager_id": target_manager_id,
        "manager_name": target_manager_data.get("name")
    }), 200


@manager_bp.post("/assign-staff")
def assign_staff_to_manager():
    """
    POST /api/manager/assign-staff
    
    Add multiple staff IDs to a manager's document (team list).
    
    Headers:
        X-User-Id: Manager's user ID
    
    Body:
        {
            "staff_ids": ["staff1", "staff2", "staff3"],
            "manager_id": "mgr123"  // Optional, defaults to X-User-Id
        }
    
    Returns:
        {
            "success": true,
            "message": "5 staff members assigned to manager",
            "manager_id": "mgr123",
            "staff_assigned": [
                {"user_id": "staff1", "name": "John Doe"},
                {"user_id": "staff2", "name": "Jane Smith"}
            ],
            "failed": []
        }
    """
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "Manager ID required via X-User-Id header"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    # Get request data
    data = request.get_json()
    staff_ids = data.get("staff_ids", [])
    target_manager_id = data.get("manager_id", manager_id)
    
    if not staff_ids or not isinstance(staff_ids, list):
        return jsonify({"error": "staff_ids must be a non-empty array"}), 400
    
    # Verify target manager
    target_manager_ref = db.collection("users").document(target_manager_id)
    target_manager_doc = target_manager_ref.get()
    
    if not target_manager_doc.exists:
        return jsonify({"error": "Target manager not found"}), 404
    
    target_manager_data = target_manager_doc.to_dict()
    if not _is_manager_role(target_manager_data.get("role", "staff")):
        return jsonify({"error": "Target user is not a manager"}), 400
    
    # Get existing team_staff_ids array (if any)
    existing_staff_ids = target_manager_data.get("team_staff_ids", [])
    
    # Process each staff member
    staff_assigned = []
    failed = []
    
    for staff_id in staff_ids:
        try:
            # Verify staff exists
            staff_ref = db.collection("users").document(staff_id)
            staff_doc = staff_ref.get()
            
            if not staff_doc.exists:
                failed.append({
                    "user_id": staff_id,
                    "error": "Staff member not found"
                })
                continue
            
            staff_data = staff_doc.to_dict()
            
            # Verify is staff role
            if staff_data.get("role") != "staff":
                failed.append({
                    "user_id": staff_id,
                    "error": "User is not a staff member"
                })
                continue
            
            # Update staff document with manager_id
            staff_ref.update({
                "manager_id": target_manager_id,
                "manager_name": target_manager_data.get("name"),
                "manager_email": target_manager_data.get("email"),
                "manager_assigned_at": now_iso(),
                "updated_at": now_iso()
            })
            
            # Add to assigned list
            staff_assigned.append({
                "user_id": staff_id,
                "name": staff_data.get("name"),
                "email": staff_data.get("email")
            })
            
            # Add to team list if not already present
            if staff_id not in existing_staff_ids:
                existing_staff_ids.append(staff_id)
        
        except Exception as e:
            failed.append({
                "user_id": staff_id,
                "error": str(e)
            })
    
    # Update manager document with team_staff_ids array
    target_manager_ref.update({
        "team_staff_ids": existing_staff_ids,
        "team_size": len(existing_staff_ids),
        "updated_at": now_iso()
    })
    
    return jsonify({
        "success": True,
        "message": f"{len(staff_assigned)} staff member(s) assigned to manager",
        "manager_id": target_manager_id,
        "manager_name": target_manager_data.get("name"),
        "staff_assigned": staff_assigned,
        "failed": failed,
        "total_team_size": len(existing_staff_ids)
    }), 200


@manager_bp.delete("/staff/<staff_id>/remove-manager")
def remove_manager_from_staff(staff_id):
    """
    DELETE /api/manager/staff/<staff_id>/remove-manager
    
    Remove manager assignment from a staff member.
    
    Headers:
        X-User-Id: Manager's user ID
    
    Returns:
        {
            "success": true,
            "message": "Manager removed from staff member"
        }
    """
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "Manager ID required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    # Get staff document
    staff_ref = db.collection("users").document(staff_id)
    staff_doc = staff_ref.get()
    
    if not staff_doc.exists:
        return jsonify({"error": "Staff member not found"}), 404
    
    staff_data = staff_doc.to_dict()
    current_manager_id = staff_data.get("manager_id")
    
    # Verify current user is the assigned manager (or admin)
    if current_manager_id != manager_id and manager_data.get("role") not in ["admin", "director"]:
        return jsonify({"error": "You are not assigned to this staff member"}), 403
    
    # Remove manager fields from staff document
    staff_ref.update({
        "manager_id": firestore.DELETE_FIELD,
        "manager_name": firestore.DELETE_FIELD,
        "manager_email": firestore.DELETE_FIELD,
        "manager_assigned_at": firestore.DELETE_FIELD,
        "updated_at": now_iso()
    })
    
    # Remove from manager's team_staff_ids array
    if current_manager_id:
        manager_ref = db.collection("users").document(current_manager_id)
        manager_doc = manager_ref.get()
        
        if manager_doc.exists:
            manager_team_data = manager_doc.to_dict()
            team_staff_ids = manager_team_data.get("team_staff_ids", [])
            
            if staff_id in team_staff_ids:
                team_staff_ids.remove(staff_id)
                manager_ref.update({
                    "team_staff_ids": team_staff_ids,
                    "team_size": len(team_staff_ids),
                    "updated_at": now_iso()
                })
    
    return jsonify({
        "success": True,
        "message": "Manager removed from staff member",
        "staff_id": staff_id
    }), 200


@manager_bp.get("/my-team")
def get_my_team():
    """
    GET /api/manager/my-team
    
    Get all staff members assigned to this manager.
    
    Headers:
        X-User-Id: Manager's user ID
    
    Returns:
        {
            "manager": {...},
            "team_staff": [
                {
                    "user_id": "staff1",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "assigned_at": "2025-01-01T00:00:00Z"
                }
            ],
            "team_size": 5
        }
    """
    db = firestore.client()
    manager_id = _get_viewer_id()
    
    if not manager_id:
        return jsonify({"error": "Manager ID required"}), 401
    
    # Verify manager access
    manager_data, error_response, status_code = _verify_manager_access(manager_id)
    if error_response:
        return error_response, status_code
    
    # Query all staff where manager_id matches
    staff_query = db.collection("users")\
        .where("manager_id", "==", manager_id)\
        .stream()
    
    team_staff = []
    for staff_doc in staff_query:
        staff_data = staff_doc.to_dict()
        team_staff.append({
            "user_id": staff_doc.id,
            "name": staff_data.get("name"),
            "email": staff_data.get("email"),
            "role": staff_data.get("role", "staff"),
            "is_active": staff_data.get("is_active", True),
            "assigned_at": staff_data.get("manager_assigned_at"),
            "created_at": staff_data.get("created_at")
        })
    
    return jsonify({
        "manager": {
            "user_id": manager_id,
            "name": manager_data.get("name"),
            "email": manager_data.get("email"),
            "role": manager_data.get("role")
        },
        "team_staff": team_staff,
        "team_size": len(team_staff)
    }), 200