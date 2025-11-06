from datetime import datetime, timezone, timedelta
import os
import re
from flask import request, jsonify
from . import notifications_bp
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from email_utils import send_email as send_email_util


def now_iso():
    return datetime.now(timezone.utc).isoformat()



def create_notification(db, user_id: str, title: str, body: str, task_id: str = None, send_email: bool = False):
    """Create an in-app notification and optionally send an email.

    Returns the notification document id on success, or None on failure.
    """
    if not user_id:
        return None

    # Only fetch user email if we plan to send an email; avoid extra DB lookups
    user_email = None
    if send_email:
        try:
            user_doc = db.collection("users").document(user_id).get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
            user_email = user_data.get("email")
        except Exception:
            user_email = None

    notif = {
        "user_id": user_id,
        "title": title,
        "body": body,
        "task_id": task_id,
        "created_at": now_iso(),
        "read": False,
        "email_sent": False,
        "email_sent_at": None,
    }

    # Create the notification document
    ref = db.collection("notifications").document()
    ref.set(notif)

    # Send email if requested and we have an address
    if send_email and user_email:
        ok = send_email_util(user_email, title, body)
        if ok:
            ref.update({"email_sent": True, "email_sent_at": now_iso()})
            # email sent; no debug print to reduce noise

    return ref.id


@notifications_bp.post("/test-email")
def test_email():
    """Send a test email directly without creating a task or notification.
    
    Request body:
      user_id - recipient user ID
      title - email subject
      body - email body
    """
    db = firestore.client()
    payload = request.get_json(force=True) or {}
    
    user_id = payload.get("user_id")
    title = payload.get("title", "Test Email")
    body = payload.get("body", "This is a test email.")
    
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    # Get user email
    user_doc = db.collection("users").document(user_id).get()
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404
    
    user_data = user_doc.to_dict()
    user_email = user_data.get("email")
    
    if not user_email:
        return jsonify({"error": "User has no email address"}), 400
    
    # Send email directly
    success = send_email_util(user_email, title, body)
    
    if success:
        return jsonify({
            "success": True,
            "message": f"Email sent to {user_email}",
            "recipient": user_email
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": "Failed to send email. Check SMTP configuration."
        }), 500


@notifications_bp.post("/check-deadlines")
def check_deadlines():
    """Check for tasks with due dates approaching and create notifications for involved users.

    Query params:
      hours - lookahead window in hours (default 24, starting from tomorrow)
    """
    db = firestore.client()
    # Allow callers to specify an explicit start/end ISO window (UTC strings).
    # If not provided, fall back to the `hours` lookahead window starting from tomorrow.
    start_iso = request.args.get("start_iso")
    end_iso = request.args.get("end_iso")
    if not start_iso or not end_iso:
        try:
            hours = int(request.args.get("hours") or 24)
        except Exception:
            hours = 24

        now = datetime.now(timezone.utc)
        # Start from tomorrow (24 hours from now)
        tomorrow = now + timedelta(hours=24)
        window_end = tomorrow + timedelta(hours=hours)
        start_iso = tomorrow.isoformat()
        end_iso = window_end.isoformat()

    # Query tasks with due_date between start_iso and end_iso (ISO strings)
    # Firestore stores due dates as strings in different formats sometimes
    # (e.g. "YYYY-MM-DDTHH:MM"). Normalize start/end ISO to match stored
    # format when possible so string comparisons behave as expected.
    try:
        sample = next(db.collection("tasks").limit(1).stream(), None)
        sample_due = None
        if sample:
            sample_due = (sample.to_dict() or {}).get("due_date")
        if isinstance(sample_due, str) and re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", sample_due):
            # store minute-resolution UTC string like '2025-10-29T08:00'
            def fmt_minute(dt: datetime) -> str:
                return dt.strftime("%Y-%m-%dT%H:%M")

            # parse the already computed ISO strings back to datetimes then
            # format them to minute-only to match stored documents
            try:
                start_dt = datetime.fromisoformat(start_iso)
                end_dt = datetime.fromisoformat(end_iso)
                start_iso_q = fmt_minute(start_dt)
                end_iso_q = fmt_minute(end_dt)
            except Exception:
                # fallback: fall back to using original strings if parsing fails
                start_iso_q = start_iso
                end_iso_q = end_iso
        else:
            start_iso_q = start_iso
            end_iso_q = end_iso
    except Exception as e:
        print(f"check_deadlines: sample lookup failed: {e}")
        start_iso_q = start_iso
        end_iso_q = end_iso

    q = db.collection("tasks").where(filter=FieldFilter("due_date", ">=", start_iso_q)).where(filter=FieldFilter("due_date", "<=", end_iso_q))
    try:
        docs_preview = [d.id for d in list(q.limit(50).stream())]
    except Exception as e:
        docs_preview = f"query-error:{e}"
        print(f"check_deadlines: query preview error: {e}")
    results = list(q.stream())
    created = 0
    resent = 0
    # Allow requester to request resending for existing notification documents
    resend_existing = str(request.args.get("resend_existing") or "").lower() in ("1", "true", "yes")
    for t in results:
        tdata = t.to_dict() or {}
        task_id = t.id
        due_date = tdata.get("due_date")
        title = tdata.get("title") or "Task"
        msg_title = f"Upcoming deadline tomorrow: {title}"
        msg_body = f"Task '{title}' is due tomorrow at {due_date}. Please review or update the task."

        user_ids = set()
        # creator
        creator = (tdata.get("created_by") or {}).get("user_id")
        if creator:
            user_ids.add(creator)
        # assignee
        assignee = (tdata.get("assigned_to") or {}).get("user_id")
        if assignee:
            user_ids.add(assignee)
        # project members
        project_id = tdata.get("project_id")
        if project_id:
            mem_q = db.collection("memberships").where(filter=FieldFilter("project_id", "==", project_id)).stream()
            for m in mem_q:
                md = m.to_dict() or {}
                uid = md.get("user_id")
                if uid:
                    user_ids.add(uid)
        for uid in user_ids:
            # Simple dedupe: check if a similar notification exists for this task & user
            # Fetch user email for debugging
            try:
                udoc = db.collection("users").document(uid).get()
                udata = udoc.to_dict() if udoc.exists else {}
                user_email = udata.get("email")
            except Exception:
                user_email = None

            existing_q = db.collection("notifications").where(filter=FieldFilter("user_id", "==", uid)).where(filter=FieldFilter("task_id", "==", task_id)).where(filter=FieldFilter("title", "==", msg_title)).limit(1).stream()
            existing_docs = list(existing_q)
            if existing_docs:
                # existing notification doc found
                existing_doc = existing_docs[0]
                existing_data = existing_doc.to_dict() or {}
                # If requested, attempt to resend email for existing notification when email hasn't been sent
                if resend_existing and not existing_data.get("email_sent") and user_email:
                    try:
                        ok = send_email_util(user_email, msg_title, msg_body)
                        if ok:
                            existing_doc.reference.update({"email_sent": True, "email_sent_at": now_iso()})
                            resent += 1
                            # resent email successfully (no verbose print)
                        else:
                            # resend failed (no verbose print)
                            pass
                    except Exception as e:
                        print(f"check_deadlines: resend exception for {existing_doc.id}: {e}")
                else:
                    # existing notification found; skipping create (no verbose print)
                    pass
                continue

            # create notification for this user (no verbose print)
            create_notification(db, uid, msg_title, msg_body, task_id=task_id, send_email=True)
            created += 1

    # Fallback / complementary path: iterate users and notify them of tasks that are due in the same window
    # This uses the same per-user logic as the due-today endpoint to ensure users who are involved
    # get an email even if the top-level task query didn't find them (covers membership/visibility edge cases).
    users_q = db.collection("users").stream()
    per_user_created = 0
    try:
        for u in users_q:
            uid = (u.to_dict() or {}).get("user_id") or u.id
            if not uid:
                continue
            per_user_created += _notify_user_due_tasks(db, uid, start_iso, end_iso)
    except Exception as e:
        print(f"check_deadlines: per-user notification pass failed: {e}")

    total_created = created + per_user_created
    return jsonify({"checked": len(results), "notifications_created": total_created}), 200


def _notify_user_due_tasks(db, user_id: str, start_iso: str, end_iso: str) -> int:
    """Find tasks due between start_iso and end_iso that involve user_id and create notifications.

    Returns number of notifications created for this user.
    """
    # Normalize per same logic as check_deadlines: many docs store minute-only
    # ISO datetimes like 'YYYY-MM-DDTHH:MM'. Detect and format accordingly.
    try:
        sample = next(db.collection("tasks").limit(1).stream(), None)
        sample_due = None
        if sample:
            sample_due = (sample.to_dict() or {}).get("due_date")
        if isinstance(sample_due, str) and re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", sample_due):
            try:
                start_dt = datetime.fromisoformat(start_iso)
                end_dt = datetime.fromisoformat(end_iso)
                start_iso_q = start_dt.strftime("%Y-%m-%dT%H:%M")
                end_iso_q = end_dt.strftime("%Y-%m-%dT%H:%M")
            except Exception:
                start_iso_q = start_iso
                end_iso_q = end_iso
        else:
            start_iso_q = start_iso
            end_iso_q = end_iso
    except Exception:
        start_iso_q = start_iso
        end_iso_q = end_iso

    q = db.collection("tasks").where(filter=FieldFilter("due_date", ">=", start_iso_q)).where(filter=FieldFilter("due_date", "<=", end_iso_q))
    docs = list(q.stream())
    created_local = 0
    for d in docs:
        data = d.to_dict() or {}
        if data.get("archived"):
            continue

        task_id = d.id
        involved = False
        creator = (data.get("created_by") or {}).get("user_id")
        if creator == user_id:
            involved = True
        assignee = (data.get("assigned_to") or {}).get("user_id")
        if assignee == user_id:
            involved = True

        if not involved:
            project_id = data.get("project_id")
            if project_id:
                mem_id = f"{project_id}_{user_id}"
                if db.collection("memberships").document(mem_id).get().exists:
                    involved = True

        if involved:
            title = data.get("title") or "Task"
            msg_title = f"Upcoming deadline tomorrow: {title}"
            msg_body = f"Task '{title}' is due tomorrow at {data.get('due_date')}. Please review or update the task."

            # Fetch user email for debugging
            try:
                udoc = db.collection("users").document(user_id).get()
                udata = udoc.to_dict() if udoc.exists else {}
                user_email = udata.get("email")
            except Exception:
                user_email = None

            # Dedupe by checking for existing notification
            existing_q = db.collection("notifications").where(filter=FieldFilter("user_id", "==", user_id)).where(filter=FieldFilter("task_id", "==", task_id)).where(filter=FieldFilter("title", "==", msg_title)).limit(1).stream()
            exists = any(existing_q)
            if exists:
                # existing notification found; skip (no verbose print)
                continue

            # create notification for this user (no verbose print)
            create_notification(db, user_id, msg_title, msg_body, task_id=task_id, send_email=True)
            created_local += 1

    # summary logging removed; only exceptions are printed
    return created_local


@notifications_bp.get("/due-today")
def due_today():
    """Return tasks due today that involve the requesting user (creator, assignee, or project member).

    Uses X-User-Id header or ?user_id query param to determine the user.
    """
    db = firestore.client()
    viewer = request.headers.get("X-User-Id") or request.args.get("user_id")
    if not viewer:
        return jsonify({"error": "user_id required via X-User-Id header or ?user_id"}), 401

    # Allow client to pass start_iso and end_iso (UTC ISO strings) to support local-day
    start_iso = request.args.get("start_iso")
    end_iso = request.args.get("end_iso")
    if not start_iso or not end_iso:
        # Determine today's UTC range as fallback
        now = datetime.now(timezone.utc)
        start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(days=1, microseconds=-1)
        start_iso = start.isoformat()
        end_iso = end.isoformat()

    # Query tasks with due_date between start and end
    q = db.collection("tasks").where(filter=FieldFilter("due_date", ">=", start_iso)).where(filter=FieldFilter("due_date", "<=", end_iso))
    # Debug prints removed: only log on exceptions
    try:
        docs_preview = [d.id for d in list(q.limit(50).stream())]
    except Exception as e:
        docs_preview = f"query-error:{e}"
        print(f"due_today: query preview error: {e}")
    docs = list(q.stream())
    res = []
    for d in docs:
        data = d.to_dict() or {}
        if data.get("archived"):
            continue

        task_id = d.id
        # Check involvement: creator, assignee, or project membership
        involved = False
        creator = (data.get("created_by") or {}).get("user_id")
        if creator == viewer:
            involved = True
        assignee = (data.get("assigned_to") or {}).get("user_id")
        if assignee == viewer:
            involved = True

        if not involved:
            project_id = data.get("project_id")
            if project_id:
                mem_id = f"{project_id}_{viewer}"
                if db.collection("memberships").document(mem_id).get().exists:
                    involved = True

        if involved:
            # Minimal task info
            res.append({
                "task_id": task_id,
                "title": data.get("title"),
                "due_date": data.get("due_date"),
                "assigned_to": data.get("assigned_to"),
                "project_id": data.get("project_id"),
            })

    return jsonify({"count": len(res), "tasks": res}), 200
