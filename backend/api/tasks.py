
from datetime import datetime, timezone
from flask import request, jsonify
from . import tasks_bp
from firebase_admin import firestore

def now_iso():
    return datetime.now(timezone.utc).isoformat()

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
        "updated_at": data.get("updated_at"),
        "created_by": data.get("created_by"),
        "assigned_to": data.get("assigned_to"),
        "project_id": data.get("project_id"),
        "labels": data.get("labels", []),
    }

def _viewer_id():
    vid = (request.headers.get("X-User-Id") or request.args.get("viewer_id") or "").strip()
    return vid

def _ensure_creator_or_404(task_doc):
    viewer = _viewer_id()
    data = task_doc.to_dict() or {}
    creator = (data.get("created_by") or {}).get("user_id")
    return bool(viewer and creator and viewer == creator)

def _require_membership(db, project_id, user_id):
    if not project_id or not user_id:
        return False
    mem_id = f"{project_id}_{user_id}"
    return db.collection("memberships").document(mem_id).get().exists

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
    }
    task_ref.set(task_doc)
    return jsonify({"task_id": task_ref.id, **task_doc}), 201

@tasks_bp.get("")
def list_tasks():
    db = firestore.client()
    viewer = _viewer_id()
    if not viewer:
        return jsonify({"error":"viewer_id required via X-User-Id header or ?viewer_id"}) ,401

    project_id = (request.args.get("project_id") or "").strip()
    assigned_to_id = (request.args.get("assigned_to_id") or "").strip()
    label_id = (request.args.get("label_id") or "").strip()
    try:
        limit = int(request.args.get("limit") or 50)
    except Exception:
        limit = 50
    limit_fetch = max(limit, 200)

    query = db.collection("tasks").where("created_by.user_id", "==", viewer)

    if project_id:
        query = query.where("project_id", "==", project_id)
    if assigned_to_id:
        query = query.where("assigned_to.user_id", "==", assigned_to_id)
    if label_id:
        query = query.where("labels", "array_contains", label_id)

    docs = list(query.limit(limit_fetch).stream())

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
    if not _ensure_creator_or_404(doc):
        return jsonify({"error": "Not found"}), 404
    return jsonify(task_to_json(doc)), 200

@tasks_bp.put("/<task_id>")
def update_task(task_id):
    db = firestore.client()
    viewer = _viewer_id()
    if not viewer:
        return jsonify({"error":"viewer_id required"}), 401
    payload = request.get_json(force=True) or {}
    doc_ref = db.collection("tasks").document(task_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Task not found"}), 404
    if (doc.to_dict().get("created_by") or {}).get("user_id") != viewer:
        return jsonify({"error":"forbidden"}), 403
    if not _ensure_creator_or_404(doc):
        return jsonify({"error": "Not found"}), 404

    updates = {}
    for field in ["title", "description", "priority", "status", "due_date", "labels"]:
        if field in payload:
            updates[field] = payload[field]
    if not updates:
        return jsonify({"error": "No fields to update"}), 400

    updates["updated_at"] = now_iso()
    doc_ref.update(updates)
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

    doc_ref.delete()
    return jsonify({"ok": True, "task_id": task_id}), 200
