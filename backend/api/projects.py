from datetime import datetime, timezone
from flask import request, jsonify
from . import projects_bp
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

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
        return jsonify({"error": "name and owner_id are required"}), 400

    # Resolve owner_id: accept uid directly, or a custom handle, or an email
    resolve_id = owner_id
    try:
        user_ref = db.collection("users").document(owner_id).get()
        if not user_ref.exists:
            q = db.collection("users").where(filter=FieldFilter("handle", "==", owner_id)).limit(1).stream()
            resolved = None
            for d in q:
                resolved = d.id
                break
            if not resolved and "@" in owner_id:
                # 3) Try by email
                q2 = db.collection("users").where(filter=FieldFilter("email", "==", owner_id.lower())).limit(1).stream()
                for d in q2:
                    resolved = d.id
                    break
            if resolved:
                resolve_id = resolved
    except Exception:
        pass

    owner_id = resolve_id

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
    
    # Get current user from header
    viewer_id = request.headers.get("X-User-Id", "").strip()
    if not viewer_id:
        return jsonify({"error": "Authentication required"}), 401
    
    # Get user info to check role
    user_doc = db.collection("users").document(viewer_id).get()
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404
    
    user_data = user_doc.to_dict()
    user_role = (user_data.get("role") or "").lower()
    
    # Admin/HR: see all projects
    if user_role in ["admin", "hr"]:
        q = db.collection("projects") \
              .order_by("created_at", direction=firestore.Query.DESCENDING) \
              .stream()
        res = [{"project_id": d.id, **d.to_dict()} for d in q]
        return jsonify(res), 200
    
    # Manager/Director: see projects they own + projects where their team members are assigned
    if user_role in ["manager", "director"]:
        # Get projects where user is owner
        owned_projects = set()
        q_owned = db.collection("projects").where(filter=FieldFilter("owner_id", "==", viewer_id)).stream()
        for doc in q_owned:
            owned_projects.add(doc.id)
        
        # Get team members
        team_member_ids = set()
        q_team = db.collection("users").where(filter=FieldFilter("manager_id", "==", viewer_id)).stream()
        for doc in q_team:
            team_member_ids.add(doc.id)
        
        # Get projects where team members are assigned
        team_projects = set()
        for member_id in team_member_ids:
            q_memberships = db.collection("memberships").where(filter=FieldFilter("user_id", "==", member_id)).stream()
            for mem in q_memberships:
                team_projects.add(mem.to_dict().get("project_id"))
        
        # Combine owned and team projects
        visible_project_ids = owned_projects | team_projects
        
        # Fetch all these projects
        all_projects = []
        q_all = db.collection("projects").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
        for doc in q_all:
            if doc.id in visible_project_ids:
                all_projects.append({"project_id": doc.id, **doc.to_dict()})
        
        return jsonify(all_projects), 200
    
    # Staff: only see projects they are assigned to
    memberships = db.collection("memberships").where(filter=FieldFilter("user_id", "==", viewer_id)).stream()
    project_ids = set()
    for mem in memberships:
        project_ids.add(mem.to_dict().get("project_id"))
    
    # Fetch these projects
    res = []
    q = db.collection("projects").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    for doc in q:
        if doc.id in project_ids:
            res.append({"project_id": doc.id, **doc.to_dict()})
    
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
    updates = {k: v for k, v in payload.items() if k in {"name", "key", "description", "archived"}}
    if not updates:
        return jsonify({"error": "No fields to update"}), 400
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
    mems = db.collection("memberships").where(filter=FieldFilter("project_id", "==", project_id)).stream()
    for m in mems:
        db.collection("memberships").document(m.id).delete()

    ref.delete()
    return jsonify({"ok": True, "project_id": project_id}), 200
