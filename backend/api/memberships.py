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
    # Determine viewer from header (optional for tests/automation)
    viewer = (request.headers.get('X-User-Id') or request.args.get('viewer_id') or '').strip()
    # If a viewer is provided, enforce RBAC (disallow staff)
    if viewer:
        try:
            vdoc = db.collection('users').document(viewer).get()
            vdata = vdoc.to_dict() if vdoc.exists else {}
            vrole = (vdata.get('role') or 'staff').lower()
        except Exception:
            vrole = 'staff'
        if vrole == 'staff':
            return jsonify({"error":"Permission denied"}), 403
    payload = request.get_json(force=True) or {}
    project_id = (payload.get("project_id") or "").strip()
    user_id = (payload.get("user_id") or "").strip()
    role = (payload.get("role") or "contributor").strip()
    if not project_id or not user_id:
        return jsonify({"error":"project_id and user_id are required"}), 400
    ref = db.collection("memberships").document(f"{project_id}_{user_id}")
    doc = {"project_id": project_id, "user_id": user_id, "role": role, "added_at": now_iso()}
    ref.set(doc)
    
    # Send notification to the new member
    try:
        # Get project details
        project_doc = db.collection("projects").document(project_id).get()
        if project_doc.exists:
            project_data = project_doc.to_dict() or {}
            project_name = project_data.get("name", "a project")
            
            # Get who added the member (viewer)
            added_by_name = "A manager"
            if viewer:
                try:
                    viewer_doc = db.collection("users").document(viewer).get()
                    if viewer_doc.exists:
                        viewer_data = viewer_doc.to_dict() or {}
                        added_by_name = viewer_data.get("name", "A manager")
                except Exception:
                    pass
            
            # Send notification
            from . import notifications as notifications_module
            notifications_module.create_notification(
                db,
                user_id,
                f"Added to project: {project_name}",
                f"{added_by_name} added you to the project '{project_name}' as a {role}.",
                task_id=None,
                send_email=True,
            )
    except Exception as e:
        print(f"Failed to send project membership notification: {e}")
    
    return jsonify(doc), 201

@memberships_bp.get("/by-project/<project_id>")
def list_project_members(project_id):
    db = firestore.client()
    q = db.collection("memberships").where(filter=FieldFilter("project_id", "==", project_id)).stream()
    res = [d.to_dict() for d in q]
    return jsonify(res), 200


@memberships_bp.delete("/<project_id>/<user_id>")
def remove_member(project_id, user_id):
    db = firestore.client()
    # Determine viewer from header (required for RBAC)
    viewer = (request.headers.get('X-User-Id') or request.args.get('viewer_id') or '').strip()
    if not viewer:
        return jsonify({"error":"viewer_id required via X-User-Id header"}), 401
    # Lookup viewer role
    try:
        vdoc = db.collection('users').document(viewer).get()
        vdata = vdoc.to_dict() if vdoc.exists else {}
        vrole = (vdata.get('role') or 'staff').lower()
    except Exception:
        vrole = 'staff'
    # Disallow staff from removing memberships
    if vrole == 'staff':
        return jsonify({"error":"Permission denied"}), 403
    doc_id = f"{project_id}_{user_id}"
    ref = db.collection("memberships").document(doc_id)
    if not ref.get().exists:
        return jsonify({"error": "Membership not found"}), 404

    # Prevent removing the project's owner via the membership endpoint
    proj_ref = db.collection("projects").document(project_id).get()
    try:
        if proj_ref.exists:
            proj = proj_ref.to_dict() or {}
            owner_id = proj.get("owner_id")
            if owner_id and owner_id == user_id:
                return jsonify({"error": "Cannot remove the project owner"}), 400
    except Exception:
        # If any error occurs resolving the project, fall back to deletion behavior below
        pass

    ref.delete()
    return jsonify({"ok": True, "project_id": project_id, "user_id": user_id}), 200