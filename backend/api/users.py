from datetime import datetime, timezone
from typing import Optional, Dict, Any

from flask import request, jsonify
from . import users_bp
from firebase_admin import firestore

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_user_by_email(db, email: str):
    q = db.collection("users").where("email", "==", email).limit(1).stream()
    for d in q:
        return {"id": d.id, **d.to_dict()}
    return None

@users_bp.post("")
def create_user():
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    user_id = (payload.get("user_id") or "").strip()
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()

    if not user_id or not name or not email:
        return jsonify({"error": "user_id, name and email are required"}), 400

    user_ref = db.collection("users").document(user_id)
    if user_ref.get().exists:
        return jsonify({"error": "User already exists"}), 409

    if get_user_by_email(db, email):
        return jsonify({"error": "Email already exists"}), 409

    user_doc = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "created_at": now_iso(),
    }
    user_ref.set(user_doc)
    return jsonify({"user": user_doc}), 201

@users_bp.get("/<user_id>")
def get_user(user_id):
    db = firestore.client()
    doc = db.collection("users").document(user_id).get()
    if not doc.exists:
        return jsonify({"error": "User not found"}), 404
    return jsonify(doc.to_dict()), 200