from datetime import datetime, timezone
from flask import request, jsonify
from . import comments_bp
from firebase_admin import firestore

def now_iso():
    return datetime.now(timezone.utc).isoformat()

@comments_bp.post("")
def add_comment():
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    task_id = (payload.get("task_id") or "").strip()
    author_id = (payload.get("author_id") or "").strip()
    body = (payload.get("body") or "").strip()
    if not task_id or not author_id or not body:
        return jsonify({"error":"task_id, author_id, body are required"}), 400
    ref = db.collection("comments").document()
    doc = {
        "task_id": task_id,
        "author_id": author_id,
        "body": body,
        "created_at": now_iso(),
        "edited_at": None,
    }
    ref.set(doc)
    return jsonify({"comment_id": ref.id, **doc}), 201

@comments_bp.get("/by-task/<task_id>")
def list_comments(task_id):
    db = firestore.client()
    q = db.collection("comments").where("task_id","==",task_id).order_by("created_at").limit(100).stream()
    res = [{"comment_id": d.id, **d.to_dict()} for d in q]
    return jsonify(res), 200