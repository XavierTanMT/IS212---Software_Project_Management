from datetime import datetime, timezone
from flask import jsonify
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
    }

def _safe_iso_to_dt(s):
    try:
        if not s:
            return None
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

@dashboard_bp.get("/users/<user_id>/dashboard")
def user_dashboard(user_id):
    db = firestore.client()

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
    return jsonify(resp), 200