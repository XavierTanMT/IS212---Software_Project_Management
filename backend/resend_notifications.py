"""Small admin script to resend emails for notifications that haven't had email_sent=True.

Usage:
  python resend_notifications.py [--dry-run] [--limit N]

This will iterate recent notifications and call send_email for those where
email_sent is False or missing. It updates the document's email_sent and
email_sent_at when successful.
"""
from dotenv import load_dotenv
import os
import argparse
from datetime import datetime, timezone

load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore
from firebase_utils import get_firebase_credentials
from email_utils import send_email


def init_firebase_app():
    if not firebase_admin._apps:
        creds = get_firebase_credentials()
        cred = credentials.Certificate(creds)
        firebase_admin.initialize_app(cred)


def main(dry_run: bool = True, limit: int = 100):
    init_firebase_app()
    db = firestore.client()

    # Fetch recent notifications (order by created_at desc). We'll filter in Python
    q = db.collection('notifications').order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
    docs = list(q.stream())
    print(f'Found {len(docs)} recent notifications (limit={limit})')

    count_sent = 0
    for d in docs:
        data = d.to_dict() or {}
        nid = d.id
        user_id = data.get('user_id')
        email_sent = data.get('email_sent')
        if email_sent:
            print(f'skipping {nid} (already email_sent=True)')
            continue

        # Look up user email
        user_doc = db.collection('users').document(user_id).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        to_email = user_data.get('email')
        if not to_email:
            print(f'skipping {nid} user={user_id} (no email on user record)')
            continue

        subject = data.get('title') or 'Notification'
        body = data.get('body') or 'You have a notification.'

        print(f"would send to {to_email}: subject='{subject}' (dry_run={dry_run})")
        if dry_run:
            continue

        ok = send_email(to_email, subject, body)
        if ok:
            db.collection('notifications').document(nid).update({
                'email_sent': True,
                'email_sent_at': datetime.now(timezone.utc).isoformat()
            })
            print(f'sent and updated {nid} -> email_sent=True')
            count_sent += 1
        else:
            print(f'failed to send for {nid}')

    print(f'Done. Emails sent: {count_sent}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Do not actually send emails or update DB')
    parser.add_argument('--limit', type=int, default=100, help='How many recent notifications to inspect')
    args = parser.parse_args()
    main(dry_run=args.dry_run, limit=args.limit)
