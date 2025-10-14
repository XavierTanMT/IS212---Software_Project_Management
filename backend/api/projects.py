
from datetime import datetime, timezone
from flask import request, jsonify
from . import projects_bp
from firebase_admin import firestore

def now_iso():
    return datetime.now(timezone.utc).isoformat()

@projects_bp.post("")
def create_project():
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    name = (payload.get("name") or "").strip()
    key = (payload.get("key") or "").strip()  # short code, e.g. TMS
    owner_id = (payload.get("owner_id") or "").strip()
    description = (payload.get("description") or "").strip()
    if not name or not owner_id:
        return jsonify({"error":"name and owner_id are required"}), 400

    # Create project
    proj_ref = db.collection("projects").document()
    project_id = proj_ref.id
    doc = {
        "name": name,
        "key": key or None,
        "description": description or None,
        "owner_id": owner_id,
        "created_at": now_iso(),
        "archived": False,
    }
    proj_ref.set(doc)

    # Ensure owner is also a member (role=owner)
    mem_id = f"{project_id}_{owner_id}"
    db.collection("memberships").document(mem_id).set({
        "membership_id": mem_id,
        "project_id": project_id,
        "user_id": owner_id,
        "role": "owner",
        "created_at": now_iso()
    })

    return jsonify({"project_id": proj_ref.id, **doc}), 201

@projects_bp.get("")
def list_projects():
    db = firestore.client()
    q = db.collection("projects").order_by("created_at", direction=firestore.Query.DESCENDING).limit(50).stream()
    res = [{"project_id": d.id, **d.to_dict()} for d in q]
    return jsonify(res), 200

@projects_bp.get("/<project_id>")
def get_project(project_id):
    db = firestore.client()
    doc = db.collection("projects").document(project_id).get()
    if not doc.exists:
        return jsonify({"error": "Project not found"}), 404
    return jsonify({"project_id": doc.id, **doc.to_dict()}), 200

@projects_bp.patch("/<project_id>")
def patch_project(project_id):
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    ref = db.collection("projects").document(project_id)
    if not ref.get().exists:
        return jsonify({"error": "Project not found"}), 404
    updates = {k: v for k, v in payload.items() if k in {"name","key","description","archived"}}
    if not updates:
        return jsonify({"error":"No fields to update"}), 400
    updates["updated_at"] = now_iso()
    ref.update(updates)
    return jsonify({"project_id": project_id, **ref.get().to_dict()}), 200

@projects_bp.delete("/<project_id>")
def delete_project(project_id):
    db = firestore.client()
    ref = db.collection("projects").document(project_id)
    if not ref.get().exists:
        return jsonify({"error": "Project not found"}), 404

    # Cleanup memberships for this project
    mems = db.collection("memberships").where("project_id","==",project_id).stream()
    for m in mems:
        db.collection("memberships").document(m.id).delete()

    ref.delete()
    return jsonify({"ok": True, "project_id": project_id}), 200
