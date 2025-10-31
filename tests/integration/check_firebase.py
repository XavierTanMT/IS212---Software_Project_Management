"""
Quick script to check Firebase configuration and quota status.
Run: python tests/integration/check_firebase.py
"""
import sys
import os

# Add backend to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

print("=" * 80)
print("FIREBASE CONFIGURATION CHECK")
print("=" * 80)

# Check 1: Environment variables
print("\n1. Checking environment variables...")
env_vars = [
    "GOOGLE_APPLICATION_CREDENTIALS",
    "FIREBASE_CREDENTIALS_JSON",
    "FIREBASE_CREDENTIALS_PATH",
    "FIRESTORE_EMULATOR_HOST",
    "FIREBASE_AUTH_EMULATOR_HOST"
]

for var in env_vars:
    value = os.environ.get(var)
    if value:
        # Don't print full credentials
        display_value = value if "HOST" in var else (value[:50] + "..." if len(value) > 50 else value)
        print(f"   ✓ {var} = {display_value}")
    else:
        print(f"   ✗ {var} not set")

# Check 2: Can we import firebase_utils?
print("\n2. Checking backend.firebase_utils...")
try:
    from backend.firebase_utils import get_firebase_credentials
    print("   ✓ firebase_utils module imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import: {e}")
    sys.exit(1)

# Check 3: Can we get credentials?
print("\n3. Checking Firebase credentials...")
try:
    creds = get_firebase_credentials()
    print(f"   ✓ Credentials loaded successfully")
    print(f"   ✓ Type: {creds.get('type', 'unknown')}")
    print(f"   ✓ Project ID: {creds.get('project_id', 'unknown')}")
    print(f"   ✓ Client Email: {creds.get('client_email', 'unknown')}")
except Exception as e:
    print(f"   ✗ Failed to get credentials: {e}")
    print(f"\n   Solutions:")
    print(f"   1. Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json")
    print(f"   2. Or use emulators: $env:FIRESTORE_EMULATOR_HOST='localhost:8080'")
    sys.exit(1)

# Check 4: Can we initialize Firebase?
print("\n4. Checking Firebase initialization...")
try:
    import firebase_admin
    from firebase_admin import credentials
    
    if firebase_admin._apps:
        print("   ✓ Firebase already initialized")
        app = firebase_admin.get_app()
    else:
        cred = credentials.Certificate(creds)
        app = firebase_admin.initialize_app(cred)
        print("   ✓ Firebase initialized successfully")
    
    print(f"   ✓ App name: {app.name}")
except Exception as e:
    print(f"   ✗ Failed to initialize: {e}")
    sys.exit(1)

# Check 5: Can we connect to Firestore?
print("\n5. Checking Firestore connection...")
try:
    from firebase_admin import firestore
    db = firestore.client()
    print("   ✓ Firestore client created")
    
    # Try a simple operation
    test_doc = db.collection("_connection_test").document("_test").get()
    print("   ✓ Connection successful")
    
    # Check if using emulator
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        print(f"   ℹ Using emulator: {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
    else:
        print("   ℹ Using production Firebase")
    
except Exception as e:
    error_msg = str(e).lower()
    if "quota exceeded" in error_msg or "resource_exhausted" in error_msg:
        print(f"   ✗ Firebase quota exceeded!")
        print(f"\n   Solutions:")
        print(f"   1. Wait until midnight Pacific Time for quota reset")
        print(f"   2. Use emulators: firebase emulators:start")
        print(f"   3. Upgrade to Blaze plan in Firebase Console")
        print(f"   4. Run unit tests only: python -m pytest tests/unit -v")
    elif "permission" in error_msg:
        print(f"   ✗ Permission denied: {e}")
        print(f"   Check service account permissions in Firebase Console")
    elif "connection" in error_msg or "network" in error_msg:
        print(f"   ✗ Connection error: {e}")
        print(f"   Check internet connection and firewall settings")
    else:
        print(f"   ✗ Error: {e}")
    sys.exit(1)

# All checks passed!
print("\n" + "=" * 80)
print("✓ ALL CHECKS PASSED - Firebase is configured correctly!")
print("=" * 80)
print("\nYou can now run integration tests:")
print("  python -m pytest tests/integration --ignore=tests/integration/archive -v")
print("\nOr run with coverage:")
print("  python -m pytest tests/integration --ignore=tests/integration/archive --cov=backend --cov-branch")
