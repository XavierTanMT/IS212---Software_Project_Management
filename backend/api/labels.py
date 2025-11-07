from datetime import datetime, timezone
from flask import request, jsonify
from . import labels_bp
from firebase_admin import firestore

def now_iso():
    return datetime.now(timezone.utc).isoformat()

@labels_bp.post("")
def create_label():
    """Create a new label."""
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    
    name = (payload.get("name") or "").strip()
    color = (payload.get("color") or "").strip()
    
    if not name:
        return jsonify({"error": "name is required"}), 400
    
    ref = db.collection("labels").document()
    label_doc = {
        "label_id": ref.id,
        "name": name,
        "color": color,
        "created_at": now_iso()
    }
    ref.set(label_doc)
    
    return jsonify(label_doc), 201

@labels_bp.get("")
def list_labels():
    """Get all labels."""
    db = firestore.client()
    labels = db.collection("labels").stream()
    result = []
    for label in labels:
        label_data = label.to_dict()
        label_data["label_id"] = label.id
        result.append(label_data)
    return jsonify(result), 200

@labels_bp.post("/assign")
def assign_label():
    """Assign a label to a task."""
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    
    task_id = (payload.get("task_id") or "").strip()
    label_id = (payload.get("label_id") or "").strip()
    
    if not task_id or not label_id:
        return jsonify({"error": "task_id and label_id are required"}), 400
    
    # Update task to add label to labels array
    task_ref = db.collection("tasks").document(task_id)
    task_doc = task_ref.get()
    
    if task_doc.exists:
        task_data = task_doc.to_dict() or {}
        labels = task_data.get("labels", [])
        if label_id not in labels:
            labels.append(label_id)
            task_ref.update({"labels": labels})
    
    # Create task_labels mapping
    db.collection("task_labels").document(f"{task_id}_{label_id}").set({
        "task_id": task_id,
        "label_id": label_id,
        "assigned_at": now_iso()
    })
    
    return jsonify({"success": True, "message": "Label assigned to task"}), 200

@labels_bp.post("/unassign")
def unassign_label():
    """Unassign a label from a task."""
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    
    task_id = (payload.get("task_id") or "").strip()
    label_id = (payload.get("label_id") or "").strip()
    
    if not task_id or not label_id:
        return jsonify({"error": "task_id and label_id are required"}), 400
    
    # Update task to remove label from labels array
    task_ref = db.collection("tasks").document(task_id)
    task_doc = task_ref.get()
    
    if task_doc.exists:
        task_data = task_doc.to_dict() or {}
        labels = task_data.get("labels", [])
        if label_id in labels:
            labels.remove(label_id)
            task_ref.update({"labels": labels})
    
    # Delete task_labels mapping
    db.collection("task_labels").document(f"{task_id}_{label_id}").delete()
    
    return jsonify({"success": True, "message": "Label unassigned from task"}), 200
