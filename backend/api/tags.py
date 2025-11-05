from flask import request, jsonify
from . import tags_bp
from firebase_admin import firestore

# Tags are simple strings (max 12 chars) stored directly on tasks
# No separate tags collection needed - just validate and store on task.tags array (max 3 tags)

@tags_bp.get("")
def list_tags():
    """Get all unique tags across all tasks"""
    db = firestore.client()
    tasks = db.collection("tasks").stream()
    tag_set = set()
    for task in tasks:
        task_data = task.to_dict() or {}
        tags = task_data.get("tags", [])
        if isinstance(tags, list):
            tag_set.update(tags)
    return jsonify(sorted(list(tag_set))), 200