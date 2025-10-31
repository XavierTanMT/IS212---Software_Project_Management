"""
Test Firebase emulator connection.
Run this to verify emulators are working correctly.
"""
import os
import sys

# Add paths
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

print("=" * 80)
print("Firebase Emulator Connection Test")
print("=" * 80)

# Step 1: Configure environment for emulators
print("\n1. Configuring environment for emulators...")
firestore_host = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
auth_host = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099")

# Set emulator environment variables
os.environ["FIRESTORE_EMULATOR_HOST"] = firestore_host
os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = auth_host
os.environ["GCLOUD_PROJECT"] = "demo-test-project"

# Set dummy credentials file path (Firebase Admin SDK requires it even for emulators)
dummy_creds_path = os.path.join(os.path.dirname(__file__), "dummy-credentials.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = dummy_creds_path

# Remove any other Firebase credentials from environment
if "FIREBASE_CREDENTIALS_JSON" in os.environ:
    del os.environ["FIREBASE_CREDENTIALS_JSON"]

print(f"   ✓ FIRESTORE_EMULATOR_HOST = {firestore_host}")
print(f"   ✓ FIREBASE_AUTH_EMULATOR_HOST = {auth_host}")
print(f"   ✓ GCLOUD_PROJECT = demo-test-project")
print(f"   ✓ Using dummy credentials for emulator: {os.path.basename(dummy_creds_path)}")

# Step 2: Check if emulators are running
print("\n2. Checking if emulators are running...")
import socket

def check_port(host_port):
    """Check if port is accessible."""
    try:
        host, port = host_port.split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except:
        return False

firestore_running = check_port(firestore_host)
auth_running = check_port(auth_host)

if firestore_running:
    print(f"   ✓ Firestore emulator running on {firestore_host}")
else:
    print(f"   ✗ Firestore emulator NOT running on {firestore_host}")
    print("     Start with: firebase emulators:start")
    sys.exit(1)

if auth_running:
    print(f"   ✓ Auth emulator running on {auth_host}")
else:
    print(f"   ✗ Auth emulator NOT running on {auth_host}")
    print("     Start with: firebase emulators:start")
    sys.exit(1)

# Step 3: Initialize Firebase
print("\n3. Initializing Firebase...")
try:
    import firebase_admin
    from firebase_admin import credentials
    
    if not firebase_admin._apps:
        # Initialize for emulator - credentials file is set via GOOGLE_APPLICATION_CREDENTIALS
        # The emulators ignore the actual credentials, but SDK requires them
        firebase_admin.initialize_app(options={'projectId': 'demo-test-project'})
    
    print("   ✓ Firebase initialized for emulator")
except Exception as e:
    print(f"   ✗ Failed to initialize Firebase: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Test Firestore connection
print("\n4. Testing Firestore connection...")
try:
    from firebase_admin import firestore
    db = firestore.client()
    
    # Try to write a test document
    test_ref = db.collection("_test").document("_connection_test")
    test_ref.set({
        "test": "data",
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    
    # Read it back
    doc = test_ref.get()
    if doc.exists:
        print("   ✓ Successfully wrote and read from Firestore emulator")
        data = doc.to_dict()
        print(f"   ✓ Test data: {data}")
    else:
        print("   ✗ Document not found after writing")
        sys.exit(1)
    
    # Clean up
    test_ref.delete()
    print("   ✓ Successfully deleted test document")
    
except Exception as e:
    print(f"   ✗ Firestore test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 5: Test Auth
print("\n5. Testing Auth emulator...")
try:
    from firebase_admin import auth
    
    # Create a test user
    test_email = "test@emulator.local"
    try:
        # Try to delete if exists
        user = auth.get_user_by_email(test_email)
        auth.delete_user(user.uid)
    except:
        pass
    
    # Create new test user
    user = auth.create_user(
        email=test_email,
        password="testpass123",
        display_name="Test User"
    )
    print(f"   ✓ Created test user: {user.uid}")
    
    # Verify user exists
    fetched_user = auth.get_user(user.uid)
    print(f"   ✓ Retrieved user: {fetched_user.email}")
    
    # Clean up
    auth.delete_user(user.uid)
    print("   ✓ Deleted test user")
    
except Exception as e:
    print(f"   ✗ Auth test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# All tests passed!
print("\n" + "=" * 80)
print("✓ ALL TESTS PASSED!")
print("=" * 80)
print("\nEmulators are working correctly. You can now run integration tests:")
print("  python -m pytest tests/integration --ignore=tests/integration/archive -v")
print("\nEmulator UI available at: http://localhost:4000")
