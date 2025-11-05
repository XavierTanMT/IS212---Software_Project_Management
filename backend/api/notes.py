from datetime import datetime, timezone
from flask import request, jsonify
from . import notes_bp
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import re

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def _get_viewer_id():
    """Extract current user ID from request headers or query params."""
    viewer_id = (request.headers.get("X-User-Id") or request.args.get("viewer_id") or "").strip()
    return viewer_id

def _extract_mentions(body):
    """Extract @mentions from note body. Returns list of unique user IDs."""
    if not body:
        return []
    # Match @username pattern (alphanumeric, underscore, hyphen)
    mentions = re.findall(r'@([a-zA-Z0-9_-]+)', body)
    # Return unique mentions
    return list(set(mentions))

@notes_bp.post("")
def add_note():
    """Add a note to a task with @mention support."""
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    task_id = (payload.get("task_id") or "").strip()
    author_id = (payload.get("author_id") or "").strip()
    body = (payload.get("body") or "").strip()
    if not task_id or not author_id or not body:
        return jsonify({"error":"task_id, author_id, body are required"}), 400
    
    # Extract mentions from body
    mentions = _extract_mentions(body)
    
    ref = db.collection("notes").document()
    doc = {
        "task_id": task_id,
        "author_id": author_id,
        "body": body,
        "mentions": mentions,
        "created_at": now_iso(),
        "edited_at": None,
    }
    ref.set(doc)
    return jsonify({"note_id": ref.id, **doc}), 201

@notes_bp.get("/by-task/<task_id>")
def list_notes(task_id):
    """List all notes for a task (excluding archived)."""
    db = firestore.client()
    q = db.collection("notes").where(filter=FieldFilter("task_id", "==", task_id)).order_by("created_at").limit(100).stream()
    res = []
    for d in q:
        note_data = d.to_dict() or {}
        # Skip archived notes
        if note_data.get("archived"):
            continue
        res.append({"note_id": d.id, **note_data})
    return jsonify(res), 200

@notes_bp.patch("/<note_id>")
def update_note(note_id):
    """Update a note. Only the author can update their own notes."""
    db = firestore.client()
    viewer_id = _get_viewer_id()
    
    if not viewer_id:
        return jsonify({"error": "Authentication required"}), 401
    
    # Get the note
    note_ref = db.collection("notes").document(note_id)
    note_doc = note_ref.get()
    
    if not note_doc.exists:
        return jsonify({"error": "Note not found"}), 404
    
    note_data = note_doc.to_dict()
    
    # Check authorization - only author can edit
    if note_data.get("author_id") != viewer_id:
        return jsonify({"error": "You can only edit your own notes"}), 403
    
    payload = request.get_json(force=True) or {}
    body = (payload.get("body") or "").strip()
    
    if not body:
        return jsonify({"error": "body is required"}), 400
    
    # Extract mentions from updated body
    mentions = _extract_mentions(body)
    
    # Update the note
    update_data = {
        "body": body,
        "mentions": mentions,
        "edited_at": now_iso()
    }
    note_ref.update(update_data)
    
    # Get updated document
    updated_doc = note_ref.get()
    return jsonify({"note_id": note_id, **updated_doc.to_dict()}), 200

@notes_bp.delete("/<note_id>")
def delete_note(note_id):
    """Delete a note. Only the author can delete their own notes."""
    db = firestore.client()
    viewer_id = _get_viewer_id()
    
    if not viewer_id:
        return jsonify({"error": "Authentication required"}), 401
    
    # Get the note
    note_ref = db.collection("notes").document(note_id)
    note_doc = note_ref.get()
    
    if not note_doc.exists:
        return jsonify({"error": "Note not found"}), 404
    
    note_data = note_doc.to_dict()
    
    # Check authorization - only author can delete
    if note_data.get("author_id") != viewer_id:
        return jsonify({"error": "You can only delete your own notes"}), 403
    
    # Delete the note
    note_ref.delete()
    
    return jsonify({"message": "Note deleted successfully"}), 200
