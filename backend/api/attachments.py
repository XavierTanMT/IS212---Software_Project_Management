from datetime import datetime, timezone
from flask import request, jsonify
from . import attachments_bp
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

def now_iso():
    return datetime.now(timezone.utc).isoformat()

@attachments_bp.post("")
def add_attachment():
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    task_id = (payload.get("task_id") or "").strip()
    file_name = (payload.get("file_name") or "").strip()
    file_path = (payload.get("file_path") or "").strip()  # e.g., gs://bucket/key
    uploaded_by = (payload.get("uploaded_by") or "").strip()
    if not task_id or not file_name or not file_path or not uploaded_by:
        return jsonify({"error":"task_id, file_name, file_path, uploaded_by are required"}), 400
    ref = db.collection("attachments").document()
    doc = {
        "task_id": task_id,
        "file_name": file_name,
        "file_path": file_path,
        "uploaded_by": uploaded_by,
        "upload_date": now_iso()
    }
    ref.set(doc)
    return jsonify({"attachment_id": ref.id, **doc}), 201

@attachments_bp.get("/by-task/<task_id>")
def list_attachments(task_id):
    db = firestore.client()
    # Try with ordering first, fallback to unordered if index doesn't exist
    try:
        q = db.collection("attachments").where(filter=FieldFilter("task_id", "==", task_id)).order_by("upload_date").stream()
        res = [{"attachment_id": d.id, **d.to_dict()} for d in q]
    except Exception as e:
        # Fallback: if composite index doesn't exist, query without ordering
        if "index" in str(e).lower():
            q = db.collection("attachments").where(filter=FieldFilter("task_id", "==", task_id)).stream()
            res = [{"attachment_id": d.id, **d.to_dict()} for d in q]
        else:
            raise
    return jsonify(res), 200