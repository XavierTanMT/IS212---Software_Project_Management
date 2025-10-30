from datetime import datetime, timezone
from flask import request, jsonify
from . import memberships_bp
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

def now_iso():
    return datetime.now(timezone.utc).isoformat()

@memberships_bp.post("")
def add_member():
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    project_id = (payload.get("project_id") or "").strip()
    user_id = (payload.get("user_id") or "").strip()
    role = (payload.get("role") or "contributor").strip()
    if not project_id or not user_id:
        return jsonify({"error":"project_id and user_id are required"}), 400
    ref = db.collection("memberships").document(f"{project_id}_{user_id}")
    doc = {"project_id": project_id, "user_id": user_id, "role": role, "added_at": now_iso()}
    ref.set(doc)
    return jsonify(doc), 201

@memberships_bp.get("/by-project/<project_id>")
def list_project_members(project_id):
    db = firestore.client()
    q = db.collection("memberships").where(filter=FieldFilter("project_id", "==", project_id)).stream()
    res = [d.to_dict() for d in q]
    return jsonify(res), 200