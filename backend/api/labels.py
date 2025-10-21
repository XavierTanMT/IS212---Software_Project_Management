from flask import request, jsonify
from . import labels_bp
from firebase_admin import firestore

@labels_bp.post("")
def create_label():
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    name = (payload.get("name") or "").strip()
    color = (payload.get("color") or "").strip()  # hex or css
    if not name:
        return jsonify({"error":"name is required"}), 400
    ref = db.collection("labels").document()
    doc = {"name": name, "color": color or None}
    ref.set(doc)
    return jsonify({"label_id": ref.id, **doc}), 201

@labels_bp.get("")
def list_labels():
    db = firestore.client()
    res = [{"label_id": d.id, **d.to_dict()} for d in db.collection("labels").stream()]
    return jsonify(res), 200

@labels_bp.post("/assign")
def assign_label():
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    task_id = (payload.get("task_id") or "").strip()
    label_id = (payload.get("label_id") or "").strip()
    if not task_id or not label_id:
        return jsonify({"error":"task_id and label_id are required"}), 400
    # store a mapping for filtering; also update task.labels array
    db.collection("task_labels").document(f"{task_id}_{label_id}").set({"task_id": task_id, "label_id": label_id})
    task_ref = db.collection("tasks").document(task_id)
    task_ref.set({"labels": firestore.ArrayUnion([label_id])}, merge=True)
    return jsonify({"ok": True}), 200

@labels_bp.post("/unassign")
def unassign_label():
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    task_id = (payload.get("task_id") or "").strip()
    label_id = (payload.get("label_id") or "").strip()
    if not task_id or not label_id:
        return jsonify({"error":"task_id and label_id are required"}), 400
    db.collection("task_labels").document(f"{task_id}_{label_id}").delete()
    task_ref = db.collection("tasks").document(task_id)
    task_ref.set({"labels": firestore.ArrayRemove([label_id])}, merge=True)
    return jsonify({"ok": True}), 200