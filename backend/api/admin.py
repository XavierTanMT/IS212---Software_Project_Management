"""
Admin endpoints for user management and system administration.
Admin extends Employee and can add/remove staff and managers.
Also includes debugging utilities for Firebase Auth and Firestore sync.
"""
from flask import request, jsonify
from . import admin_bp
from firebase_admin import auth, firestore
from datetime import datetime, timezone

def now_iso():
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()

def _get_admin_id():
    """Extract admin user ID from request headers or query params."""
    admin_id = (request.headers.get("X-User-Id") or request.args.get("admin_id") or "").strip()
    return admin_id

def _verify_admin_access(admin_id):
    """Verify user is an admin."""
    db = firestore.client()
    admin_doc = db.collection("users").document(admin_id).get()
    
    if not admin_doc.exists:
        return None, jsonify({"error": "Admin user not found"}), 404
    
    admin_data = admin_doc.to_dict()
    if admin_data.get("role") != "admin":
        return None, jsonify({"error": "Admin access required"}), 403
    
    return admin_data, None, None

# ========== DASHBOARD & STATISTICS ==========

@admin_bp.get("/dashboard")
def get_admin_dashboard():
    """
    Admin dashboard - System-wide overview.
    Returns statistics about users, tasks, and projects.
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    # Get all users
    users_query = db.collection("users").stream()
    all_users = []
    role_breakdown = {
        "staff": 0,
        "manager": 0,
        "director": 0,
        "hr": 0,
        "admin": 0
    }
    active_users = 0
    
    for user_doc in users_query:
        user_data = user_doc.to_dict()
        user_data["user_id"] = user_doc.id
        all_users.append(user_data)
        
        role = user_data.get("role", "staff")
        if role in role_breakdown:
            role_breakdown[role] += 1
        
        if user_data.get("is_active", True):
            active_users += 1
    
    # Get all tasks
    tasks_query = db.collection("tasks").stream()
    all_tasks = []
    status_breakdown = {}
    priority_breakdown = {}
    
    for task_doc in tasks_query:
        task_data = task_doc.to_dict()
        task_data["task_id"] = task_doc.id
        all_tasks.append(task_data)
        
        status = task_data.get("status", "To Do")
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        priority = task_data.get("priority", 5)
        priority_breakdown[f"Priority {priority}"] = priority_breakdown.get(f"Priority {priority}", 0) + 1
    
    # Get all projects
    projects_query = db.collection("projects").stream()
    all_projects = []
    
    for project_doc in projects_query:
        project_data = project_doc.to_dict()
        project_data["project_id"] = project_doc.id
        all_projects.append(project_data)
    
    # Sort users by creation date (most recent first)
    sorted_users = sorted(all_users, key=lambda x: x.get("created_at", ""), reverse=True)
    
    return jsonify({
        "view": "admin",
        "admin": {
            "user_id": admin_id,
            "name": admin_data.get("name"),
            "email": admin_data.get("email"),
            "role": "admin"
        },
        "statistics": {
            "total_users": len(all_users),
            "active_users": active_users,
            "inactive_users": len(all_users) - active_users,
            "users_by_role": role_breakdown,
            "total_tasks": len(all_tasks),
            "tasks_by_status": status_breakdown,
            "tasks_by_priority": priority_breakdown,
            "total_projects": len(all_projects)
        },
        "recent_users": sorted_users[:10],
        "recent_tasks": sorted(all_tasks, key=lambda x: x.get("created_at", ""), reverse=True)[:20],
        "all_projects": all_projects
    }), 200

@admin_bp.get("/statistics")
def get_system_statistics():
    """Get detailed system analytics."""
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    # Calculate statistics
    users_count = len(list(db.collection("users").stream()))
    tasks_count = len(list(db.collection("tasks").stream()))
    projects_count = len(list(db.collection("projects").stream()))
    memberships_count = len(list(db.collection("memberships").stream()))
    
    return jsonify({
        "system_statistics": {
            "users": users_count,
            "tasks": tasks_count,
            "projects": projects_count,
            "project_memberships": memberships_count,
            "average_tasks_per_user": round(tasks_count / users_count, 2) if users_count > 0 else 0,
            "average_members_per_project": round(memberships_count / projects_count, 2) if projects_count > 0 else 0
        },
        "generated_at": now_iso()
    }), 200

# ========== USER MANAGEMENT (Admin.addStaff, Admin.addManager, Admin.removeStaff, Admin.removeManager) ==========

@admin_bp.get("/users")
def get_all_users():
    """
    Get all users in the system.
    Admin can see everyone.
    
    Query params:
    - role: Filter by role (staff, manager, director, hr, admin)
    - status: Filter by status (active, inactive)
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    # Get query parameters
    role_filter = request.args.get("role")
    status_filter = request.args.get("status")
    
    users = []
    users_query = db.collection("users").stream()
    
    for user_doc in users_query:
        user_data = user_doc.to_dict()
        user_data["user_id"] = user_doc.id
        
        # Apply role filter
        if role_filter and user_data.get("role") != role_filter:
            continue
        
        # Apply status filter
        is_active = user_data.get("is_active", True)
        if status_filter == "active" and not is_active:
            continue
        if status_filter == "inactive" and is_active:
            continue
        
        users.append(user_data)
    
    return jsonify({
        "users": users,
        "total": len(users),
        "filters": {
            "role": role_filter,
            "status": status_filter
        }
    }), 200

@admin_bp.post("/staff")
def add_staff():
    """
    Add new staff member - Admin.addStaff(Employee) from class diagram.
    
    Body: {
        "email": "user@example.com",
        "password": "password123",
        "name": "John Doe"
    }
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    
    # Validate required fields
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    
    if not email or not password or not name:
        return jsonify({"error": "email, password, and name are required"}), 400
    
    try:
        # Create Firebase Auth user
        firebase_user = auth.create_user(
            email=email,
            password=password,
            display_name=name
        )
        
        # Create Firestore document with staff role
        staff_doc = {
            "user_id": firebase_user.uid,
            "name": name,
            "email": email,
            "role": "staff",
            "created_at": now_iso(),
            "created_by": admin_id,
            "firebase_uid": firebase_user.uid,
            "is_active": True
        }
        
        db.collection("users").document(firebase_user.uid).set(staff_doc)
        
        return jsonify({
            "success": True,
            "message": "Staff member added successfully",
            "user": staff_doc
        }), 201
        
    except auth.EmailAlreadyExistsError:
        return jsonify({"error": "Email already exists"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to add staff: {str(e)}"}), 500

@admin_bp.post("/managers")
def add_manager():
    """
    Add new manager - Admin.addManager(Manager) from class diagram.
    
    Body: {
        "email": "manager@example.com",
        "password": "password123",
        "name": "Jane Smith",
        "manager_type": "manager" // or "director" or "hr"
    }
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    
    # Validate required fields
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    manager_type = data.get("manager_type", "manager")
    
    if not email or not password or not name:
        return jsonify({"error": "email, password, and name are required"}), 400
    
    # Validate manager type
    valid_manager_types = ["manager", "director", "hr"]
    if manager_type not in valid_manager_types:
        return jsonify({"error": f"manager_type must be one of: {valid_manager_types}"}), 400
    
    try:
        # Create Firebase Auth user
        firebase_user = auth.create_user(
            email=email,
            password=password,
            display_name=name
        )
        
        # Create Firestore document with manager role
        manager_doc = {
            "user_id": firebase_user.uid,
            "name": name,
            "email": email,
            "role": manager_type,
            "created_at": now_iso(),
            "created_by": admin_id,
            "firebase_uid": firebase_user.uid,
            "is_active": True
        }
        
        db.collection("users").document(firebase_user.uid).set(manager_doc)
        
        return jsonify({
            "success": True,
            "message": f"Manager ({manager_type}) added successfully",
            "user": manager_doc
        }), 201
        
    except auth.EmailAlreadyExistsError:
        return jsonify({"error": "Email already exists"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to add manager: {str(e)}"}), 500

@admin_bp.delete("/staff/<user_id>")
def remove_staff(user_id):
    """
    Remove staff member - Admin.removeStaff(Employee) from class diagram.
    Soft delete (deactivates user).
    
    Query params:
    - hard_delete=true (optional, permanently deletes user)
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    hard_delete = request.args.get('hard_delete', '').lower() == 'true'
    
    # Get user
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404
    
    user_data = user_doc.to_dict()
    
    # Verify user is staff
    if user_data.get("role") != "staff":
        return jsonify({
            "error": "This endpoint is for removing staff only",
            "user_role": user_data.get("role"),
            "message": f"Use DELETE /admin/managers/{user_id} for managers"
        }), 400
    
    if hard_delete:
        # Hard delete
        user_ref.delete()
        try:
            auth.delete_user(user_id)
        except Exception:
            pass
        
        return jsonify({
            "success": True,
            "message": "Staff member permanently deleted",
            "user_id": user_id,
            "deleted_type": "hard_delete"
        }), 200
    else:
        # Soft delete (deactivate)
        user_ref.update({
            "is_active": False,
            "removed_at": now_iso(),
            "removed_by": admin_id
        })
        
        # Disable in Firebase Auth
        try:
            auth.update_user(user_id, disabled=True)
        except Exception:
            pass
        
        return jsonify({
            "success": True,
            "message": "Staff member deactivated",
            "user_id": user_id,
            "deleted_type": "soft_delete"
        }), 200

@admin_bp.delete("/managers/<user_id>")
def remove_manager(user_id):
    """
    Remove manager - Admin.removeManager(Manager) from class diagram.
    Soft delete (deactivates user).
    
    Query params:
    - hard_delete=true (optional, permanently deletes user)
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    hard_delete = request.args.get('hard_delete', '').lower() == 'true'
    
    # Get user
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404
    
    user_data = user_doc.to_dict()
    
    # Verify user is manager
    manager_roles = ["manager", "director", "hr"]
    if user_data.get("role") not in manager_roles:
        return jsonify({
            "error": "This endpoint is for removing managers only",
            "user_role": user_data.get("role"),
            "message": f"Use DELETE /admin/staff/{user_id} for staff"
        }), 400
    
    if hard_delete:
        # Hard delete
        user_ref.delete()
        try:
            auth.delete_user(user_id)
        except Exception:
            pass
        
        return jsonify({
            "success": True,
            "message": "Manager permanently deleted",
            "user_id": user_id,
            "deleted_type": "hard_delete"
        }), 200
    else:
        # Soft delete (deactivate)
        user_ref.update({
            "is_active": False,
            "removed_at": now_iso(),
            "removed_by": admin_id
        })
        
        # Disable in Firebase Auth
        try:
            auth.update_user(user_id, disabled=True)
        except Exception:
            pass
        
        return jsonify({
            "success": True,
            "message": "Manager deactivated",
            "user_id": user_id,
            "deleted_type": "soft_delete"
        }), 200

@admin_bp.put("/users/<user_id>/role")
def change_user_role(user_id):
    """
    Change user role.
    
    Body: {
        "role": "staff" | "manager" | "director" | "hr" | "admin"
    }
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    new_role = data.get("role")
    
    # Validate role
    valid_roles = ["staff", "manager", "director", "hr", "admin"]
    if new_role not in valid_roles:
        return jsonify({"error": f"Invalid role. Must be one of: {valid_roles}"}), 400
    
    # Get user
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404
    
    # Prevent changing own role
    if user_id == admin_id:
        return jsonify({"error": "Cannot change your own role"}), 400
    
    # Update role
    user_ref.update({
        "role": new_role,
        "updated_at": now_iso(),
        "updated_by": admin_id
    })
    
    return jsonify({
        "success": True,
        "message": f"User role changed to {new_role}",
        "user_id": user_id,
        "new_role": new_role
    }), 200

@admin_bp.put("/users/<user_id>/status")
def change_user_status(user_id):
    """
    Activate or deactivate user.
    
    Body: {
        "is_active": true | false
    }
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    is_active = data.get("is_active")
    
    if not isinstance(is_active, bool):
        return jsonify({"error": "is_active must be true or false"}), 400
    
    # Get user
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404
    
    # Prevent deactivating own account
    if user_id == admin_id and not is_active:
        return jsonify({"error": "Cannot deactivate your own admin account"}), 400
    
    # Update status
    user_ref.update({
        "is_active": is_active,
        "updated_at": now_iso(),
        "updated_by": admin_id
    })
    
    # Update Firebase Auth
    try:
        auth.update_user(user_id, disabled=not is_active)
    except Exception:
        pass
    
    return jsonify({
        "success": True,
        "message": f"User {'activated' if is_active else 'deactivated'}",
        "user_id": user_id,
        "is_active": is_active
    }), 200

# ========== SYSTEM OVERVIEW (Read-only for Admin) ==========

@admin_bp.get("/projects")
def get_all_projects():
    """
    Get all projects in the system.
    Admin can view all projects (but not manage them like Manager does).
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    projects = []
    projects_query = db.collection("projects").stream()
    
    for project_doc in projects_query:
        project_data = project_doc.to_dict()
        project_data["project_id"] = project_doc.id
        
        # Get member count
        memberships = db.collection("memberships").where("project_id", "==", project_doc.id).stream()
        project_data["member_count"] = len(list(memberships))
        
        projects.append(project_data)
    
    return jsonify({
        "projects": projects,
        "total": len(projects)
    }), 200

@admin_bp.get("/tasks")
def get_all_tasks():
    """
    Get all tasks in the system.
    Admin can view all tasks (but not manage them like Manager does).
    
    Query params:
    - status: Filter by status
    - priority: Filter by priority
    """
    db = firestore.client()
    admin_id = _get_admin_id()
    
    if not admin_id:
        return jsonify({"error": "admin_id required via X-User-Id header or ?admin_id"}), 401
    
    # Verify admin access
    admin_data, error_response, status_code = _verify_admin_access(admin_id)
    if error_response:
        return error_response, status_code
    
    # Get query parameters
    status_filter = request.args.get("status")
    priority_filter = request.args.get("priority")
    
    tasks = []
    tasks_query = db.collection("tasks").stream()
    
    for task_doc in tasks_query:
        task_data = task_doc.to_dict()
        task_data["task_id"] = task_doc.id
        
        # Apply filters
        if status_filter and task_data.get("status") != status_filter:
            continue
        if priority_filter and str(task_data.get("priority")) != priority_filter:
            continue
        
        tasks.append(task_data)
    
    return jsonify({
        "tasks": tasks,
        "total": len(tasks),
        "filters": {
            "status": status_filter,
            "priority": priority_filter
        }
    }), 200

# ========== DEBUGGING & SYNC UTILITIES ==========

@admin_bp.get("/check/<user_id>")
def check_user_sync(user_id):
    """
    Check if user exists in both Firebase Auth and Firestore.
    Useful for diagnosing sync issues.
    
    Returns: {
        "user_id": "...",
        "in_firestore": true/false,
        "in_firebase_auth": true/false,
        "synced": true/false,
        "firestore_data": {...},
        "firebase_data": {...}
    }
    """
    db = firestore.client()
    
    # Check Firestore
    firestore_doc = db.collection("users").document(user_id).get()
    in_firestore = firestore_doc.exists
    firestore_data = firestore_doc.to_dict() if in_firestore else None
    
    # Check Firebase Auth
    in_firebase_auth = False
    firebase_data = None
    try:
        firebase_user = auth.get_user(user_id)
        in_firebase_auth = True
        firebase_data = {
            "uid": firebase_user.uid,
            "email": firebase_user.email,
            "display_name": firebase_user.display_name,
            "disabled": firebase_user.disabled,
            "email_verified": firebase_user.email_verified
        }
    except auth.UserNotFoundError:
        in_firebase_auth = False
    except Exception as e:
        firebase_data = {"error": str(e)}
    
    synced = in_firestore == in_firebase_auth
    
    return jsonify({
        "user_id": user_id,
        "in_firestore": in_firestore,
        "in_firebase_auth": in_firebase_auth,
        "synced": synced,
        "status": "✅ Synced" if synced else "⚠️ Out of sync",
        "firestore_data": firestore_data,
        "firebase_data": firebase_data,
        "recommendation": _get_recommendation(in_firestore, in_firebase_auth)
    }), 200

@admin_bp.delete("/cleanup/<user_id>")
def cleanup_user(user_id):
    """
    Clean up orphaned user data.
    Removes user from both Firebase Auth and Firestore.
    Use with caution!
    
    Query params:
    - confirm=true (required for safety)
    """
    confirm = request.args.get('confirm', '').lower() == 'true'
    
    if not confirm:
        return jsonify({
            "error": "Confirmation required",
            "message": "Add ?confirm=true to delete user data",
            "warning": "This will permanently delete the user from both Firebase Auth and Firestore"
        }), 400
    
    db = firestore.client()
    results = {
        "user_id": user_id,
        "firestore_deleted": False,
        "firebase_auth_deleted": False,
        "errors": []
    }
    
    # Delete from Firestore
    try:
        user_ref = db.collection("users").document(user_id)
        if user_ref.get().exists:
            user_ref.delete()
            results["firestore_deleted"] = True
        else:
            results["errors"].append("User not found in Firestore")
    except Exception as e:
        results["errors"].append(f"Firestore deletion failed: {str(e)}")
    
    # Delete from Firebase Auth
    try:
        auth.delete_user(user_id)
        results["firebase_auth_deleted"] = True
    except auth.UserNotFoundError:
        results["errors"].append("User not found in Firebase Auth")
    except Exception as e:
        results["errors"].append(f"Firebase Auth deletion failed: {str(e)}")
    
    if results["firestore_deleted"] or results["firebase_auth_deleted"]:
        results["status"] = "✅ Cleanup completed"
        return jsonify(results), 200
    else:
        results["status"] = "❌ Nothing to clean up"
        return jsonify(results), 404

@admin_bp.post("/sync/<user_id>")
def sync_user(user_id):
    """
    Attempt to sync user between Firebase Auth and Firestore.
    
    Cases handled:
    1. In Firestore only → Create Firebase Auth user (requires password in body)
    2. In Firebase Auth only → Create Firestore document
    
    Body for case 1: {"password": "..."}
    """
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    
    # Check current state
    firestore_doc = db.collection("users").document(user_id).get()
    in_firestore = firestore_doc.exists
    
    in_firebase_auth = False
    try:
        firebase_user = auth.get_user(user_id)
        in_firebase_auth = True
    except auth.UserNotFoundError:
        in_firebase_auth = False
    
    # Case 1: In Firestore only (orphaned Firestore doc)
    if in_firestore and not in_firebase_auth:
        firestore_data = firestore_doc.to_dict()
        password = payload.get("password", "").strip()
        
        if not password:
            return jsonify({
                "error": "Password required",
                "message": "User exists in Firestore but not Firebase Auth. Provide password to create Firebase Auth user.",
                "user_data": firestore_data
            }), 400
        
        try:
            # Create Firebase Auth user
            firebase_user = auth.create_user(
                uid=user_id,
                email=firestore_data.get("email"),
                password=password,
                display_name=firestore_data.get("name")
            )
            
            # Update Firestore with firebase_uid
            db.collection("users").document(user_id).update({
                "firebase_uid": firebase_user.uid
            })
            
            return jsonify({
                "status": "✅ Synced",
                "message": "Created Firebase Auth user for existing Firestore document",
                "user_id": user_id
            }), 201
            
        except Exception as e:
            return jsonify({
                "error": f"Failed to create Firebase Auth user: {str(e)}"
            }), 500
    
    # Case 2: In Firebase Auth only (orphaned Firebase Auth)
    elif in_firebase_auth and not in_firestore:
        firebase_user = auth.get_user(user_id)
        
        # Create Firestore document from Firebase Auth data
        user_doc = {
            "user_id": user_id,
            "name": firebase_user.display_name or "Unknown",
            "email": firebase_user.email,
            "created_at": now_iso(),
            "firebase_uid": firebase_user.uid,
            "role": "staff",
            "is_active": True
        }
        
        db.collection("users").document(user_id).set(user_doc)
        
        return jsonify({
            "status": "✅ Synced",
            "message": "Created Firestore document for existing Firebase Auth user",
            "user_id": user_id,
            "user_data": user_doc
        }), 201
    
    # Case 3: Already synced
    elif in_firestore and in_firebase_auth:
        return jsonify({
            "status": "✅ Already synced",
            "message": "User exists in both Firebase Auth and Firestore",
            "user_id": user_id
        }), 200
    
    # Case 4: Doesn't exist anywhere
    else:
        return jsonify({
            "status": "❌ Not found",
            "message": "User doesn't exist in Firebase Auth or Firestore",
            "user_id": user_id
        }), 404

def _get_recommendation(in_firestore, in_firebase_auth):
    """Generate recommendation based on sync status."""
    if in_firestore and in_firebase_auth:
        return "User is properly synced"
    elif in_firestore and not in_firebase_auth:
        return "⚠️ Orphaned Firestore document. Use DELETE /admin/cleanup or POST /admin/sync to fix."
    elif in_firebase_auth and not in_firestore:
        return "⚠️ Orphaned Firebase Auth user. Use POST /admin/sync to create Firestore document."
    else:
        return "User doesn't exist. Safe to register."