
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from firebase_admin import auth as admin_auth, firestore

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def upsert_user_profile(db, uid: str, email: str, name: Optional[str] = None, extra: Optional[Dict[str, Any]] = None):
    ref = db.collection("users").document(uid)
    snap = ref.get()
    base_doc = {
        "user_id": uid,           # keep compatibility with existing front-end
        "email": email,
        "name": name or "",
        "updated_at": now_iso(),
        "last_login_at": now_iso(),
    }
    if not snap.exists:
        base_doc["created_at"] = now_iso()
    if extra:
        base_doc.update(extra)
    ref.set(base_doc, merge=True)
    return ref.get().to_dict()

@auth_bp.post("/session")
def create_session():
    """
    Verifies a Firebase ID token from Authorization: Bearer <idToken>.
    Ensures a Firestore user profile exists (users/{uid}) and updates last_login_at.
    Accepts optional JSON with additional profile fields to store (e.g., name, address).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing Bearer token"}), 401
    id_token = auth_header.split(" ", 1)[1].strip()
    if not id_token:
        return jsonify({"error": "Empty token"}), 401

    try:
        decoded = admin_auth.verify_id_token(id_token)
    except Exception as e:
        return jsonify({"error": f"Invalid token: {str(e)}"}), 401

    uid = decoded.get("uid")
    email = decoded.get("email") or ""
    name = decoded.get("name") or ""

    db = firestore.client()
    extra = {}
    try:
        payload = request.get_json(silent=True) or {}
        # allow frontend to pass profile fields to merge, but constrain keys
        for key in ["name", "fullName", "address"]:
            if key in payload:
                extra[key] = payload[key]
        # normalize 'fullName' -> 'name'
        if "fullName" in extra and not extra.get("name"):
            extra["name"] = extra.pop("fullName")
    except Exception:
        pass

    profile = upsert_user_profile(db, uid, email, name=name, extra=extra)

    return jsonify({
        "user": {
            "uid": uid,
            "email": email,
            "name": profile.get("name") or name or "",
        }
    }), 200
