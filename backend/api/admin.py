"""
Admin utility endpoints for debugging and cleanup.
These endpoints help diagnose and fix user sync issues between Firebase Auth and Firestore.
"""
from flask import request, jsonify
from . import users_bp
from firebase_admin import auth, firestore

@users_bp.get("/admin/check/<user_id>")
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

@users_bp.delete("/admin/cleanup/<user_id>")
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

@users_bp.post("/admin/sync/<user_id>")
def sync_user(user_id):
    """
    Attempt to sync user between Firebase Auth and Firestore.
    
    Cases handled:
    1. In Firestore only → Create Firebase Auth user (requires email/password in body)
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
        from datetime import datetime, timezone
        user_doc = {
            "user_id": user_id,
            "name": firebase_user.display_name or "Unknown",
            "email": firebase_user.email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "firebase_uid": firebase_user.uid
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
