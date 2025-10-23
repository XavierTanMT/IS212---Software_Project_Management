from datetime import datetime, timezone, timedelta
from flask import jsonify, request
from . import dashboard_bp
from firebase_admin import firestore

def task_to_json(d):
    data = d.to_dict()
    return {
        "task_id": d.id,
        "title": data.get("title"),
        "description": data.get("description"),
        "priority": data.get("priority", "Medium"),
        "status": data.get("status", "To Do"),
        "due_date": data.get("due_date"),
        "created_at": data.get("created_at"),
        "created_by": data.get("created_by"),
        "assigned_to": data.get("assigned_to"),
        "project_id": data.get("project_id"),
        "labels": data.get("labels", []),
    }

def enrich_task_with_timeline_status(task):
    """Add timeline-specific status flags to task"""
    due_date = task.get("due_date")
    status = task.get("status", "To Do")
    
    # Completed tasks should not appear in overdue/timeline categories
    if status == "Completed":
        task["timeline_status"] = "completed"
        task["is_overdue"] = False
        task["is_upcoming"] = False
        return task
    
    if not due_date:
        task["timeline_status"] = "no_due_date"
        task["is_overdue"] = False
        task["is_upcoming"] = False
        return task
    
    due_dt = _safe_iso_to_dt(due_date)
    if not due_dt:
        task["timeline_status"] = "invalid_date"
        task["is_overdue"] = False
        task["is_upcoming"] = False
        return task
    
    now = datetime.now(timezone.utc)
    time_diff = due_dt - now
    total_seconds = time_diff.total_seconds()
    
    # Use total_seconds to avoid .days truncation issues
    # Use slightly relaxed boundaries to handle execution timing variations
    ONE_DAY = 86400
    
    if total_seconds < 0:
        task["timeline_status"] = "overdue"
        task["is_overdue"] = True
        task["is_upcoming"] = False
    elif total_seconds < ONE_DAY - 60:  # Less than ~24 hours (today) - 60 sec buffer for timing
        task["timeline_status"] = "today"
        task["is_overdue"] = False
        task["is_upcoming"] = True
    elif total_seconds < ONE_DAY * 7.5:  # 1-7 days (use 7.5 as boundary)
        task["timeline_status"] = "this_week"
        task["is_overdue"] = False
        task["is_upcoming"] = True
    else:  # 7.5+ days (effectively 8+ days)
        task["timeline_status"] = "future"
        task["is_overdue"] = False
        task["is_upcoming"] = False
    
    return task

def group_tasks_by_timeline(tasks):
    """Group tasks by timeline periods (excludes completed tasks)"""
    timeline = {
        "overdue": [],
        "today": [],
        "this_week": [],
        "future": [],
        "no_due_date": []
    }
    
    for task in tasks:
        enriched_task = enrich_task_with_timeline_status(task)
        status = enriched_task.get("timeline_status", "no_due_date")
        
        # Skip completed tasks - they shouldn't appear in timeline view
        if status == "completed":
            continue
            
        if status in timeline:
            timeline[status].append(enriched_task)
    
    return timeline

def detect_conflicts(tasks):
    """Detect tasks with overlapping due dates"""
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

def _safe_iso_to_dt(s):
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

@dashboard_bp.get("/users/<user_id>/dashboard")
def user_dashboard(user_id):
    db = firestore.client()
    view_mode = request.args.get("view_mode", "grid")

    user_doc = db.collection("users").document(user_id).get()
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404

    # Avoid composite index by NOT using order_by on a different field than the filter.
    created_stream = db.collection("tasks").where("created_by.user_id", "==", user_id).stream()
    assigned_stream = db.collection("tasks").where("assigned_to.user_id", "==", user_id).stream()

    # Convert to JSON and sort locally by created_at desc
    created_tasks = sorted(
        (task_to_json(d) for d in created_stream),
        key=lambda t: (_safe_iso_to_dt(t.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True
    )
    assigned_tasks = sorted(
        (task_to_json(d) for d in assigned_stream),
        key=lambda t: (_safe_iso_to_dt(t.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True
    )

    # Combine all tasks for timeline view
    all_tasks = created_tasks + assigned_tasks
    # Remove duplicates (task might be both created by and assigned to same person)
    seen_tasks = set()
    unique_tasks = []
    for task in all_tasks:
        task_id = task["task_id"]
        if task_id not in seen_tasks:
            seen_tasks.add(task_id)
            unique_tasks.append(task)

    # Status + priority breakdown (based on created tasks)
    status_breakdown = {}
    priority_breakdown = {}
    overdue_count = 0
    now = datetime.now(timezone.utc)

    for t in created_tasks:
        status_breakdown[t["status"]] = status_breakdown.get(t["status"], 0) + 1
        priority_breakdown[t["priority"]] = priority_breakdown.get(t["priority"], 0) + 1

        due = t.get("due_date")
        due_dt = _safe_iso_to_dt(due)
        if due_dt and due_dt < now and t.get("status") != "Completed":
            overdue_count += 1

    resp = {
        "statistics": {
            "total_created": len(created_tasks),
            "total_assigned": len(assigned_tasks),
            "status_breakdown": status_breakdown,
            "priority_breakdown": priority_breakdown,
            "overdue_count": overdue_count,
        },
        "recent_created_tasks": created_tasks[:5],
        "recent_assigned_tasks": assigned_tasks[:5],
    }

    # Add timeline data if requested
    if view_mode == "timeline":
        timeline_data = group_tasks_by_timeline(unique_tasks)
        conflicts = detect_conflicts(unique_tasks)
        
        resp["timeline"] = timeline_data
        resp["conflicts"] = conflicts
        resp["timeline_statistics"] = {
            "total_tasks": len(unique_tasks),
            "overdue_count": len(timeline_data["overdue"]),
            "today_count": len(timeline_data["today"]),
            "this_week_count": len(timeline_data["this_week"]),
            "future_count": len(timeline_data["future"]),
            "no_due_date_count": len(timeline_data["no_due_date"]),
            "conflict_count": len(conflicts)
        }

    return jsonify(resp), 200