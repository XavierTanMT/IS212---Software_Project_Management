#!/usr/bin/env python3
"""Test script to verify Firebase credential loading."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from firebase_utils import get_firebase_credentials

try:
    creds = get_firebase_credentials()
    print("✓ Firebase credentials loaded successfully!")
    print(f"  Project ID: {creds.get('project_id')}")
    print(f"  Client Email: {creds.get('client_email')}")
    print(f"  Type: {creds.get('type')}")
    print("\n✅ Firebase configuration is working correctly!")
except ValueError as e:
    print(f"❌ Error loading credentials: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
