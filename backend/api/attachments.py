from datetime import datetime, timezone
from flask import request, jsonify
from . import attachments_bp
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import hashlib

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# Allowed MIME types and extensions
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    'application/vnd.ms-excel',  # .xls
    'text/csv',
    'image/png',
    'image/jpeg',
    'text/plain',
    'text/markdown',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
    'application/zip',
    'application/x-zip-compressed'
}

ALLOWED_EXTENSIONS = {
    '.pdf', '.docx', '.xlsx', '.xls', '.csv', 
    '.png', '.jpg', '.jpeg', '.txt', '.md', '.pptx', '.zip'
}

# Blocked extensions (executables/scripts)
BLOCKED_EXTENSIONS = {
    '.exe', '.bat', '.sh', '.js', '.cmd', '.com', '.app',
    '.vbs', '.ps1', '.jar', '.dmg', '.deb', '.rpm'
}

# Firestore documents have a 1MB limit
# Base64 encoding increases size by ~33%, so max original file size is ~700KB
MAX_FILE_SIZE = 700 * 1024  # 700 KB (to stay under Firestore's 1MB limit after Base64 encoding)

def is_allowed_file(filename, mime_type, file_size):
    """Validate file based on extension, MIME type, and size"""
    if not filename or not mime_type:
        return False, "Missing filename or MIME type"
    
    # Check file size
    if file_size > MAX_FILE_SIZE:
        return False, f"File size exceeds 50 MB limit (got {file_size / (1024*1024):.2f} MB)"
    
    # Check for blocked extensions
    import os
    _, ext = os.path.splitext(filename.lower())
    if ext in BLOCKED_EXTENSIONS:
        return False, f"File type not allowed: {ext}"
    
    # Check if extension is allowed
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type not supported: {ext}"
    
    # Check MIME type
    if mime_type not in ALLOWED_MIME_TYPES:
        return False, f"MIME type not allowed: {mime_type}"
    
    return True, "OK"

@attachments_bp.post("")
def add_attachment():
    """Add attachment with file data stored as Base64 in Firestore (FREE - no Storage needed!)"""
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    
    task_id = (payload.get("task_id") or "").strip()
    filename = (payload.get("filename") or "").strip()
    mime_type = (payload.get("mime_type") or "").strip()
    size_bytes = payload.get("size_bytes", 0)
    uploaded_by = (payload.get("uploaded_by") or "").strip()
    file_data = payload.get("file_data", "")  # Base64 encoded file
    file_hash = (payload.get("file_hash") or "").strip()
    
    if not all([task_id, filename, mime_type, uploaded_by, file_data]):
        return jsonify({"error": "task_id, filename, mime_type, uploaded_by, and file_data are required"}), 400
    
    # Validate file
    is_valid, error_msg = is_allowed_file(filename, mime_type, size_bytes)
    if not is_valid:
        return jsonify({"error": error_msg}), 400
    
    # Note: Firestore documents have a 1MB limit, so we check file size
    # Base64 encoding increases size by ~33%
    estimated_size = len(file_data)
    if estimated_size > 900000:  # ~900KB limit to be safe
        return jsonify({
            "error": f"File too large for Firestore storage. Maximum ~700KB after Base64 encoding. Your file is ~{estimated_size/1000:.0f}KB encoded."
        }), 400
    
    ref = db.collection("attachments").document()
    doc = {
        "task_id": task_id,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "uploaded_by": uploaded_by,
        "uploaded_at": now_iso(),
        "file_data": file_data,  # Store Base64 data directly
        "file_hash": file_hash
    }
    ref.set(doc)
    
    # Return without file_data to save bandwidth
    response_doc = {k: v for k, v in doc.items() if k != 'file_data'}
    return jsonify({"attachment_id": ref.id, **response_doc}), 201

@attachments_bp.get("/by-task/<task_id>")
def list_attachments(task_id):
    """Get all attachments for a task"""
    db = firestore.client()
    try:
        q = db.collection("attachments").where(filter=FieldFilter("task_id", "==", task_id)).order_by("uploaded_at", direction=firestore.Query.DESCENDING).stream()
        res = [{"attachment_id": d.id, **d.to_dict()} for d in q]
    except Exception as e:
        # Fallback: if composite index doesn't exist, query without ordering
        if "index" in str(e).lower():
            q = db.collection("attachments").where(filter=FieldFilter("task_id", "==", task_id)).stream()
            res = [{"attachment_id": d.id, **d.to_dict()} for d in q]
            # Sort in Python
            res.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
        else:
            raise
    return jsonify(res), 200

@attachments_bp.delete("/<attachment_id>")
def delete_attachment(attachment_id):
    """Delete an attachment (Base64 data stored in Firestore)"""
    db = firestore.client()
    doc_ref = db.collection("attachments").document(attachment_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return jsonify({"error": "Attachment not found"}), 404
    
    # Simply delete the Firestore document (file data is in the document)
    doc_ref.delete()
    return jsonify({"message": "Attachment deleted"}), 200
