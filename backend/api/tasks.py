from datetime import datetime, timezone, timedelta
from flask import request, jsonify
from . import tasks_bp
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def task_to_json(d):
    data = d.to_dict() or {}
    return {
        "task_id": d.id,
        "title": data.get("title"),
        "description": data.get("description"),
        "priority": data.get("priority", "Medium"),
        "status": data.get("status", "To Do"),
        "due_date": data.get("due_date"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "created_by": data.get("created_by"),
        "assigned_to": data.get("assigned_to"),
        "project_id": data.get("project_id"),
        "labels": data.get("labels", []),
        # archival flags
        "archived": data.get("archived", False),
        "archived_at": data.get("archived_at"),
        "archived_by": data.get("archived_by"),
        # recurring task fields
        "is_recurring": data.get("is_recurring", False),
        "recurrence_interval_days": data.get("recurrence_interval_days"),
        "parent_recurring_task_id": data.get("parent_recurring_task_id"),
    }

def _viewer_id():
    vid = (request.headers.get("X-User-Id") or request.args.get("viewer_id") or "").strip()
    return vid

def _ensure_creator_or_404(task_doc):
    viewer = _viewer_id()
    data = task_doc.to_dict() or {}
    creator = (data.get("created_by") or {}).get("user_id")
    return bool(viewer and creator and viewer == creator)

def _can_edit_task(task_doc):
    """Check if user can edit task (creator OR assignee)"""
    viewer = _viewer_id()
    if not viewer:
        return False
    
    data = task_doc.to_dict() or {}
    creator = (data.get("created_by") or {}).get("user_id")
    assignee = (data.get("assigned_to") or {}).get("user_id")
    
    return viewer == creator or viewer == assignee

def _require_membership(db, project_id, user_id):
    if not project_id or not user_id:
        return False
    mem_id = f"{project_id}_{user_id}"
    return db.collection("memberships").document(mem_id).get().exists

def _notify_task_changes(db, task_id, old_data, updates, editor_id, notifications_module):
    """Send notification emails about task changes to relevant users."""
    
    # Build list of changes
    changes = []
    field_names = {
        "title": "Title",
        "description": "Description",
        "priority": "Priority",
        "status": "Status",
        "due_date": "Due Date",
        "labels": "Labels"
    }
    
    for field, new_value in updates.items():
        if field in field_names and field in old_data:
            old_value = old_data.get(field)
            if old_value != new_value:
                # Format the change message
                if field == "labels":
                    old_str = ", ".join(old_value) if old_value else "None"
                    new_str = ", ".join(new_value) if new_value else "None"
                else:
                    old_str = str(old_value) if old_value else "None"
                    new_str = str(new_value) if new_value else "None"
                
                changes.append(f"• {field_names[field]}: {old_str} → {new_str}")
    
    if not changes:
        return  # No significant changes to notify about
    
    # Get editor name. Prefer information already present in old_data
    editor_name = "Someone"
    try:
        if (old_data.get("created_by") or {}).get("user_id") == editor_id:
            editor_name = (old_data.get("created_by") or {}).get("name") or "Someone"
        elif (old_data.get("assigned_to") or {}).get("user_id") == editor_id:
            editor_name = (old_data.get("assigned_to") or {}).get("name") or "Someone"
        else:
            # Fall back to DB lookup only if necessary
            editor_doc = db.collection("users").document(editor_id).get()
            if editor_doc.exists:
                editor_data = editor_doc.to_dict() or {}
                editor_name = editor_data.get("name", "Someone")
    except Exception:
        # In tests/mocks this may fail; default to generic name
        editor_name = "Someone"
    
    # Determine who to notify
    task_title = updates.get("title", old_data.get("title", "Task"))
    recipients = set()
    
    # Notify creator (everyone gets notified, including editor)
    creator_id = (old_data.get("created_by") or {}).get("user_id")
    if creator_id:
        recipients.add(creator_id)
    
    # Notify assignee (everyone gets notified, including editor)
    assignee_id = (old_data.get("assigned_to") or {}).get("user_id")
    if assignee_id:
        recipients.add(assignee_id)
    
    # Notify project members (if task is in a project)
    project_id = old_data.get("project_id")
    if project_id:
        mem_q = db.collection("memberships").where(
            filter=FieldFilter("project_id", "==", project_id)
        ).stream()
        for m in mem_q:
            md = m.to_dict() or {}
            uid = md.get("user_id")
            if uid:
                recipients.add(uid)
    
    # Send notification to each recipient
    changes_text = "\n".join(changes)
    notification_title = f"Task Updated: {task_title}"
    notification_body = f"{editor_name} made changes to the task:\n\n{changes_text}"
    
    for user_id in recipients:
        try:
            # Create in-app notification. Defer/send emails via background job or
            # the notifications service to avoid extra DB lookups during request-based flows.
            notifications_module.create_notification(
                db,
                user_id,
                notification_title,
                notification_body,
                task_id=task_id,
                send_email=False,
            )
        except Exception as e:
            print(f"Failed to notify user {user_id} about task changes: {e}")

def _create_next_recurring_task(db, completed_task_doc):
    """
    Create the next occurrence of a recurring task.
    Called when a recurring task is marked as completed.
    
    The new task will:
    - Copy all fields except due_date, status, created_at, updated_at, archived fields
    - Calculate new due_date based on the original due_date + interval
    - Link back to original recurring task via parent_recurring_task_id
    """
    task_data = completed_task_doc.to_dict() or {}
    
    # Only create next task if this is a recurring task
    if not task_data.get("is_recurring"):
        return None
    
    interval_days = task_data.get("recurrence_interval_days")
    if not interval_days or interval_days <= 0:
        return None
    
    original_due_date = task_data.get("due_date")
    if not original_due_date:
        return None
    
    # Calculate next due date from original due date + interval
    try:
        due_dt = datetime.fromisoformat(original_due_date.replace("Z", "+00:00"))
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        
        next_due_dt = due_dt + timedelta(days=interval_days)
        next_due_date = next_due_dt.isoformat()
    except Exception:
        return None
    
    # Create new task with same properties
    new_task_ref = db.collection("tasks").document()
    new_task_data = {
        "title": task_data.get("title"),
        "description": task_data.get("description"),
        "priority": task_data.get("priority", "Medium"),
        "status": "To Do",  # Reset to To Do
        "due_date": next_due_date,
        "created_at": now_iso(),
        "updated_at": None,
        "project_id": task_data.get("project_id"),
        "labels": task_data.get("labels", []),
        "archived": False,
        "archived_at": None,
        "archived_by": None,
        "created_by": task_data.get("created_by"),
        "assigned_to": task_data.get("assigned_to"),
        # Recurring fields
        "is_recurring": True,
        "recurrence_interval_days": interval_days,
        "parent_recurring_task_id": completed_task_doc.id,  # Link to original task
    }
    
    new_task_ref.set(new_task_data)
    return new_task_ref.id

@tasks_bp.post("")
def create_task():
    db = firestore.client()
    payload = request.get_json(force=True) or {}

    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    priority = payload.get("priority", "Medium")
    status = payload.get("status", "To Do")
    due_date = payload.get("due_date")
    project_id = (payload.get("project_id") or "").strip()
    created_by_id = (payload.get("created_by_id") or "").strip()
    assigned_to_id = (payload.get("assigned_to_id") or "").strip()
    labels = payload.get("labels") or []

    if not title or len(title) < 3:
        return jsonify({"error": "Title must be at least 3 characters"}), 400
    if not description or len(description) < 10:
        return jsonify({"error": "Description must be at least 10 characters"}), 400
    if not created_by_id:
        return jsonify({"error": "created_by_id is required"}), 400

    created_by_doc = db.collection("users").document(created_by_id).get()
    if not created_by_doc.exists:
        return jsonify({"error": "created_by user not found"}), 404
    created_by = created_by_doc.to_dict()

    if project_id:
        if not _require_membership(db, project_id, created_by_id):
            return jsonify({"error": "Creator is not a member of this project"}), 403

    assigned_to = None
    if assigned_to_id:
        assigned_doc = db.collection("users").document(assigned_to_id).get()
        if not assigned_doc.exists:
            return jsonify({"error": "assigned_to user not found"}), 404
        assigned_to = assigned_doc.to_dict()

    if not isinstance(labels, list):
        labels = []
    labels = [str(x).strip() for x in labels if str(x).strip()]

    # Handle recurring task fields
    is_recurring = payload.get("is_recurring", False)
    recurrence_interval_days = payload.get("recurrence_interval_days")
    
    # Validate recurring parameters
    if is_recurring:
        if not due_date:
            return jsonify({"error": "Recurring tasks must have a due date"}), 400
        if not recurrence_interval_days or recurrence_interval_days <= 0:
            return jsonify({"error": "Recurring tasks must have a positive interval in days"}), 400

    task_ref = db.collection("tasks").document()
    task_doc = {
        "title": title,
        "description": description,
        "priority": priority,
        "status": status,
        "due_date": due_date,
        "created_at": now_iso(),
        "updated_at": None,
        "project_id": (project_id or None),
        "labels": labels,
        # archival defaults
        "archived": False,
        "archived_at": None,
        "archived_by": None,
        "created_by": {
            "user_id": created_by["user_id"],
            "name": created_by.get("name"),
            "email": created_by.get("email"),
        },
        "assigned_to": None if not assigned_to else {
            "user_id": assigned_to["user_id"],
            "name": assigned_to.get("name"),
            "email": assigned_to.get("email"),
        },
        # recurring fields
        "is_recurring": is_recurring,
        "recurrence_interval_days": recurrence_interval_days if is_recurring else None,
        "parent_recurring_task_id": None,
    }
    task_ref.set(task_doc)
    # Notify assignee if present
    if assigned_to_id:
        try:
            # Late import to avoid circular imports
            from . import notifications as notifications_module
            notifications_module.create_notification(
                db,
                assigned_to_id,
                f"Assigned: {title}",
                f"You were assigned to task '{title}'. Due: {due_date}",
                task_id=task_ref.id,
                send_email=True,
            )
        except Exception as e:
            print(f"Failed to create assignment notification: {e}")

    return jsonify({"task_id": task_ref.id, **task_doc}), 201

@tasks_bp.get("")
def list_tasks():
    db = firestore.client()
    viewer = _viewer_id()
    if not viewer:
        return jsonify({"error": "viewer_id required via X-User-Id header or ?viewer_id"}), 401

    project_id = (request.args.get("project_id") or "").strip()
    assigned_to_id = (request.args.get("assigned_to_id") or "").strip()
    label_id = (request.args.get("label_id") or "").strip()
    try:
        limit = int(request.args.get("limit") or 50)
    except Exception:
        limit = 50
    limit_fetch = max(limit, 200)

    # Determine viewer role
    viewer_doc = db.collection("users").document(viewer).get()
    viewer_data = (viewer_doc.to_dict() or {}) if viewer_doc.exists else {}
    viewer_role = (viewer_data.get("role") or "staff").lower()

    include_archived = (request.args.get("include_archived") or "").lower() in ("1", "true", "yes")

    # We'll collect matching docs from multiple queries and dedupe by id
    docs_by_id = {}

    def add_docs(q):
        try:
            for d in q.stream():
                docs_by_id[d.id] = d
        except Exception:
            pass

    # Helper to apply optional server-side narrow filters (project/label/assigned_to)
    def apply_filters(query_obj):
        q = query_obj
        if project_id:
            q = q.where(filter=FieldFilter("project_id", "==", project_id))
        if assigned_to_id:
            q = q.where(filter=FieldFilter("assigned_to.user_id", "==", assigned_to_id))
        if label_id:
            q = q.where(filter=FieldFilter("labels", "array_contains", label_id))
        return q

    # Admins see everything
    if viewer_role == 'admin':
        q = db.collection("tasks")
        q = apply_filters(q)
        add_docs(q.limit(limit_fetch))
    else:
        # Everyone can see tasks they created
        q1 = apply_filters(db.collection("tasks").where(filter=FieldFilter("created_by.user_id", "==", viewer)))
        add_docs(q1.limit(limit_fetch))

        # Everyone can see tasks assigned to them
        q2 = apply_filters(db.collection("tasks").where(filter=FieldFilter("assigned_to.user_id", "==", viewer)))
        add_docs(q2.limit(limit_fetch))

        # Managers (and similar roles) can see team members' tasks
        manager_roles = ["manager", "director", "hr"]
        if viewer_role in manager_roles:
            # Find team members (users who have manager_id == viewer)
            try:
                team_q = db.collection("users").where(filter=FieldFilter("manager_id", "==", viewer)).stream()
                team_ids = [u.id for u in team_q if u.exists]
            except Exception:
                team_ids = []

            # If we have team ids, query tasks created_by or assigned_to any of them
            if team_ids:
                # Firestore 'in' supports up to 10 items; chunk if necessary
                def chunks(lst, n):
                    for i in range(0, len(lst), n):
                        yield lst[i:i+n]

                for chunk in chunks(team_ids, 10):
                    q3 = apply_filters(db.collection("tasks").where(filter=FieldFilter("created_by.user_id", "in", chunk)))
                    add_docs(q3.limit(limit_fetch))
                    q4 = apply_filters(db.collection("tasks").where(filter=FieldFilter("assigned_to.user_id", "in", chunk)))
                    add_docs(q4.limit(limit_fetch))

    # Convert to list and post-filter archived unless explicitly included
    docs = [d for d in docs_by_id.values()]
    if not include_archived:
        docs = [d for d in docs if not ((d.to_dict() or {}).get("archived", False))]

    # Sort by created_at desc and limit
    def _key(d):
        v = (d.to_dict() or {}).get("created_at") or ""
        return v

    docs.sort(key=_key, reverse=True)
    docs = docs[:limit]

    return jsonify([task_to_json(d) for d in docs]), 200

@tasks_bp.get("/<task_id>")
def get_task(task_id):
    db = firestore.client()
    doc = db.collection("tasks").document(task_id).get()
    if not doc.exists:
        return jsonify({"error": "Task not found"}), 404
    # Allow creator or assignee, or manager/admin visibility
    viewer = _viewer_id()
    if not viewer:
        return jsonify({"error": "viewer_id required via X-User-Id header or ?viewer_id"}), 401

    data = doc.to_dict() or {}
    creator_id = (data.get("created_by") or {}).get("user_id")
    assignee_id = (data.get("assigned_to") or {}).get("user_id")

    if viewer == creator_id or viewer == assignee_id:
        return jsonify(task_to_json(doc)), 200

    # Check viewer role
    viewer_doc = db.collection("users").document(viewer).get()
    viewer_data = (viewer_doc.to_dict() or {}) if viewer_doc.exists else {}
    viewer_role = (viewer_data.get("role") or "staff").lower()
    if viewer_role == 'admin':
        return jsonify(task_to_json(doc)), 200

    manager_roles = ["manager", "director", "hr"]
    if viewer_role in manager_roles:
        # Allow if the creator or assignee report to this manager
        try:
            def is_managed_by(user_id, manager_id):
                if not user_id or not manager_id:
                    return False
                u = db.collection("users").document(user_id).get()
                if not u.exists:
                    return False
                ud = u.to_dict() or {}
                return ud.get("manager_id") == manager_id

            if is_managed_by(creator_id, viewer) or is_managed_by(assignee_id, viewer):
                return jsonify(task_to_json(doc)), 200
        except Exception:
            pass

    return jsonify({"error": "Not found"}), 404

@tasks_bp.put("/<task_id>")
def update_task(task_id):
    db = firestore.client()
    viewer = _viewer_id()
    if not viewer:
        return jsonify({"error": "viewer_id required"}), 401

    payload = request.get_json(force=True) or {}
    doc_ref = db.collection("tasks").document(task_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Task not found"}), 404
    
    # Check if user can edit task (creator OR assignee)
    if not _can_edit_task(doc):
        return jsonify({"error":"forbidden"}), 403

    current_data = doc.to_dict() or {}
    current_status = current_data.get("status")
    
    updates = {}
    for field in ["title", "description", "priority", "status", "due_date", "labels"]:
        if field in payload:
            updates[field] = payload[field]
    
    # Handle recurring task fields
    if "is_recurring" in payload:
        updates["is_recurring"] = payload["is_recurring"]
    if "recurrence_interval_days" in payload:
        updates["recurrence_interval_days"] = payload["recurrence_interval_days"]
    
    # Validate recurring parameters if being updated
    if updates.get("is_recurring"):
        interval = updates.get("recurrence_interval_days", current_data.get("recurrence_interval_days"))
        due_date = updates.get("due_date", current_data.get("due_date"))
        if not due_date:
            return jsonify({"error": "Recurring tasks must have a due date"}), 400
        if not interval or interval <= 0:
            return jsonify({"error": "Recurring tasks must have a positive interval in days"}), 400
    
    if not updates:
        return jsonify({"error": "No fields to update"}), 400

    # Validate due_date if being updated
    if "due_date" in updates and updates["due_date"]:
        try:
            # Parse the date - allow past dates for timeline rescheduling
            due_dt = datetime.fromisoformat(updates["due_date"].replace("Z", "+00:00"))
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            # Note: Removed the "must be in future" restriction to allow drag-to-overdue
        except Exception:
            return jsonify({"error": "Invalid due date format"}), 400

    updates["updated_at"] = now_iso()
    doc_ref.update(updates)
    
    # Send notification email about task changes
    try:
        from . import notifications as notifications_module
        _notify_task_changes(db, task_id, current_data, updates, viewer, notifications_module)
    except Exception as e:
        print(f"Failed to send task update notifications: {e}")
    
    # Check if task was just completed and is recurring
    new_status = updates.get("status")
    is_recurring = current_data.get("is_recurring", False)
    
    if new_status == "Completed" and current_status != "Completed" and is_recurring:
        # Task was just marked as completed - create next recurring task
        updated_doc = doc_ref.get()
        next_task_id = _create_next_recurring_task(db, updated_doc)
        response_data = task_to_json(updated_doc)
        if next_task_id:
            response_data["next_recurring_task_id"] = next_task_id
        return jsonify(response_data), 200
    
    return jsonify(task_to_json(doc_ref.get())), 200

@tasks_bp.delete("/<task_id>")
def delete_task(task_id):
    db = firestore.client()
    doc_ref = db.collection("tasks").document(task_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Task not found"}), 404
    if not _ensure_creator_or_404(doc):
        return jsonify({"error": "Not found"}), 404

    # Soft delete → archive
    viewer = _viewer_id() or ((doc.to_dict() or {}).get("created_by") or {}).get("user_id")
    doc_ref.update({
        "archived": True,
        "archived_at": now_iso(),
        "archived_by": viewer
    })
    return jsonify({"ok": True, "task_id": task_id, "archived": True}), 200


@tasks_bp.patch("/<task_id>/reassign")
def reassign_task(task_id):
    """Reassign a task to a different user (manager+ only)"""
    db = firestore.client()
    
    # Get viewer ID
    viewer_id = _viewer_id()
    if not viewer_id:
        return jsonify({"error": "viewer_id required via X-User-Id header or ?viewer_id"}), 401
    
    # Get request data
    payload = request.get_json(force=True) or {}
    new_assigned_to_id = (payload.get("new_assigned_to_id") or "").strip()
    
    if not new_assigned_to_id:
        return jsonify({"error": "new_assigned_to_id is required"}), 400
    
    # Check if viewer is a manager or above
    viewer_doc = db.collection("users").document(viewer_id).get()
    if not viewer_doc.exists:
        return jsonify({"error": "Viewer not found"}), 404
    
    viewer_data = viewer_doc.to_dict() or {}
    viewer_role = viewer_data.get("role", "staff")
    manager_roles = ["manager", "director", "hr"]
    
    if viewer_role not in manager_roles:
        return jsonify({"error": "Only managers and above can reassign tasks"}), 403
    
    # Get the task
    task_ref = db.collection("tasks").document(task_id)
    task_doc = task_ref.get()
    
    if not task_doc.exists:
        return jsonify({"error": "Task not found"}), 404
    
    task_data = task_doc.to_dict() or {}
    current_assigned_to = task_data.get("assigned_to") or {}
    current_assigned_to_id = current_assigned_to.get("user_id") if isinstance(current_assigned_to, dict) else None
    
    # Check if already assigned to the same person
    if current_assigned_to_id == new_assigned_to_id:
        return jsonify({
            "ok": True,
            "message": f"Task is already assigned to user {new_assigned_to_id}"
        }), 200
    
    # Get new assignee details
    new_assignee_doc = db.collection("users").document(new_assigned_to_id).get()
    if not new_assignee_doc.exists:
        return jsonify({"error": "New assignee user not found"}), 404
    
    new_assignee_data = new_assignee_doc.to_dict() or {}
    
    # Update the task
    task_ref.update({
        "assigned_to": {
            "user_id": new_assigned_to_id,
            "name": new_assignee_data.get("name", ""),
            "email": new_assignee_data.get("email", "")
        },
        "updated_at": now_iso()
    })
    # Notify new assignee and previous assignee (if any)
    try:
        from . import notifications as notifications_module
        # Notify new assignee
        notifications_module.create_notification(
            db,
            new_assigned_to_id,
            "Task assigned to you",
            f"You were assigned to task '{task_id}'.",
            task_id=task_id,
            send_email=True,
        )
        # Notify previous assignee they were unassigned
        if current_assigned_to_id and current_assigned_to_id != new_assigned_to_id:
            notifications_module.create_notification(
                db,
                current_assigned_to_id,
                "Task reassigned",
                f"Task '{task_id}' was reassigned to another user.",
                task_id=task_id,
                send_email=False,
            )
    except Exception as e:
        print(f"Failed to create reassignment notifications: {e}")

    return jsonify({
        "ok": True,
        "task_id": task_id,
        "assigned_to": {
            "user_id": new_assigned_to_id,
            "name": new_assignee_data.get("name", ""),
            "email": new_assignee_data.get("email", "")
        },
        "message": "Task reassigned successfully"
    }), 200

