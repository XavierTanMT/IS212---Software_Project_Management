"""Shared pytest configuration for integration tests."""
import sys
import os
import json
import pytest
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure repo root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Configure Firebase emulators for integration tests
# This prevents quota issues and makes tests faster
def configure_emulators():
    """Configure Firebase emulators for testing."""
    # Set emulator environment variables if not already set
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
        print("ℹ Setting FIRESTORE_EMULATOR_HOST=localhost:8080")
    
    if not os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
        os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = "localhost:9099"
        print("ℹ Setting FIREBASE_AUTH_EMULATOR_HOST=localhost:9099")
    
    # Disable SSL for emulators
    os.environ["FIREBASE_EMULATOR_HUB"] = "localhost:4400"
    
    # CRITICAL: Set GCLOUD_PROJECT to prevent credential lookup
    # This is required for firebase-admin SDK to work with emulators
    # See: https://github.com/firebase/firebase-admin-python/issues/227
    os.environ["GCLOUD_PROJECT"] = "demo-test-project"
    
    # CRITICAL: Set GOOGLE_APPLICATION_CREDENTIALS to dummy credentials file
    # Firebase Admin SDK needs SOME credentials file even with emulators
    # The emulators ignore the credentials, but the SDK requires them
    dummy_creds_path = os.path.join(os.path.dirname(__file__), "dummy-credentials.json")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = dummy_creds_path
    
    # Remove any Firebase credentials JSON from environment
    if "FIREBASE_CREDENTIALS_JSON" in os.environ:
        print("ℹ Removing FIREBASE_CREDENTIALS_JSON for emulator mode")
        del os.environ["FIREBASE_CREDENTIALS_JSON"]
    
    print(f"ℹ Firestore Emulator: {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
    print(f"ℹ Auth Emulator: {os.environ.get('FIREBASE_AUTH_EMULATOR_HOST')}")
    print(f"ℹ GCloud Project: {os.environ.get('GCLOUD_PROJECT')}")
    print(f"ℹ Dummy Credentials: {dummy_creds_path}")

# Configure emulators at module load time
configure_emulators()

# # CRITICAL: Clean up unit test mocks IMMEDIATELY at module load time
# # This must happen BEFORE any other imports in this file
print("=" * 80)
print("INTEGRATION TEST SETUP: Cleaning up unit test mocks...")
print("=" * 80)

for module_name in list(sys.modules.keys()):
    if module_name.startswith('firebase_admin'):
        module = sys.modules[module_name]
        if not hasattr(module, '__file__'):
            print(f"  Removing mock Firebase module: {module_name}")
            del sys.modules[module_name]

# Remove backend modules that may have imported mocked firebase
backend_modules = [m for m in sys.modules.keys() if m.startswith('backend')]
for module_name in backend_modules:
    print(f"  Removing backend module: {module_name}")
    del sys.modules[module_name]

print("=" * 80)


# Pytest hook to auto-skip integration tests if Firebase is not available
def pytest_collection_modifyitems(config, items):
    """Automatically skip integration tests if Firebase emulators are not running."""
    # Check if emulators are available
    import socket
    
    def check_emulator(host, port):
        """Check if emulator is running on host:port."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    # Parse emulator hosts
    firestore_host = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
    auth_host = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099")
    
    firestore_parts = firestore_host.split(":")
    auth_parts = auth_host.split(":")
    
    firestore_running = check_emulator(firestore_parts[0], int(firestore_parts[1]))
    auth_running = check_emulator(auth_parts[0], int(auth_parts[1]))
    
    if not (firestore_running and auth_running):
        skip_marker = pytest.mark.skip(
            reason=f"Firebase emulators not running. Start with: firebase emulators:start\n"
                   f"  Firestore ({firestore_host}): {'✓ Running' if firestore_running else '✗ Not running'}\n"
                   f"  Auth ({auth_host}): {'✓ Running' if auth_running else '✗ Not running'}"
        )
        for item in items:
            # Skip all tests in the integration folder
            if "integration" in str(item.fspath):
                item.add_marker(skip_marker)



# DO NOT import Firebase at module level - use lazy imports to avoid slowdown
# This makes test collection much faster

_firebase_initialized = False

def ensure_firebase_initialized():
    """Ensure Firebase is initialized for emulator use."""
    global _firebase_initialized
    
    # Lazy import - only load when actually needed
    import firebase_admin
    from firebase_admin import credentials
    
    # Check if firebase_admin has any apps - this is the real indicator
    if firebase_admin._apps:
        _firebase_initialized = True
        return
    
    # If we thought we initialized but _apps is empty, we need to reinitialize
    if _firebase_initialized and not firebase_admin._apps:
        _firebase_initialized = False
    
    if not _firebase_initialized:
        try:
            # Initialize Firebase with emulator support
            # When using emulators, we don't need real credentials
            if os.environ.get("FIRESTORE_EMULATOR_HOST"):
                print("ℹ Initializing Firebase for emulator use...")
                # For emulators, we need to bypass credential checking
                # The trick is to monkey-patch or use an internal class
                # Let's try using Certificate with minimal valid JSON
                try:
                    # Create a mock credential that won't be validated by emulator
                    import firebase_admin._http_client
                    # Use the internal EmptyCredentials if available
                    mock_cred = firebase_admin._http_client.EmptyCredentials()
                    firebase_admin.initialize_app(mock_cred, {'projectId': 'demo-test'})
                except (AttributeError, TypeError):
                    # Fallback: just initialize with options, errors will be caught below
                    firebase_admin.initialize_app(options={'projectId': 'demo-test'})
            else:
                # Fallback to real Firebase if emulators not configured
                from backend.firebase_utils import get_firebase_credentials
                firebase_creds = get_firebase_credentials()
                cred = credentials.Certificate(firebase_creds)
                firebase_admin.initialize_app(cred)
            
            _firebase_initialized = True
            print("✓ Firebase initialized successfully")
        except Exception as e:
            print(f"✗ Firebase initialization failed: {e}")
            # For emulators, this shouldn't happen, but if it does, skip tests
            if os.environ.get("FIRESTORE_EMULATOR_HOST"):
                pytest.skip(f"Failed to initialize Firebase for emulator: {e}")
            else:
                pytest.skip(f"Failed to initialize Firebase: {e}")


@pytest.fixture
def app():
    """Create Flask application for testing."""
    # Ensure Firebase is properly initialized before creating app
    ensure_firebase_initialized()
    
    # Import and create the app
    # The cleanup_unit_test_mocks fixture ensures we're using real Firebase
    from backend.app import create_app
    
    app = create_app()
    app.config['TESTING'] = True
    
    yield app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def db():
    """Get Firestore database instance (emulator or real)."""
    # Ensure Firebase is initialized before creating client
    ensure_firebase_initialized()
    
    from firebase_admin import firestore as real_firestore
    
    # Get Firestore client from the real module
    client = real_firestore.client()
    
    # Validate that we have a proper Firestore client with required methods
    if not hasattr(client, 'collection'):
        raise RuntimeError(
            f"Firestore client is invalid (type: {type(client)}). "
            "Check Firebase initialization and credentials."
        )
    
    # Check if we're using emulator
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        print(f"ℹ Using Firestore Emulator: {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
    else:
        print("ℹ Using production Firestore (not recommended for tests)")
        # Test connection and check for quota errors
        try:
            test_doc = client.collection("_connection_test").document("_test").get()
        except Exception as e:
            error_msg = str(e).lower()
            if "quota exceeded" in error_msg or "resource_exhausted" in error_msg:
                pytest.skip(
                    "Firebase quota exceeded. Please use emulators:\n"
                    "  1. Install: npm install -g firebase-tools\n"
                    "  2. Start: firebase emulators:start\n"
                    "  3. Tests will automatically detect and use emulators"
                )
            elif "permission" in error_msg or "denied" in error_msg:
                pytest.skip(f"Firebase permission denied: {e}")
            elif "connection" in error_msg or "network" in error_msg:
                pytest.skip(f"Firebase connection error: {e}")
    
    return client


@pytest.fixture
def test_collection_prefix():
    """Prefix for test collections to isolate test data."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"test_{timestamp}"


@pytest.fixture
def cleanup_collections(db, test_collection_prefix):
    """Cleanup test collections after tests."""
    collections_to_clean = []
    
    yield collections_to_clean
    
    # Cleanup after test
    for collection_name in collections_to_clean:
        try:
            docs = db.collection(collection_name).limit(100).stream()
            for doc in docs:
                doc.reference.delete()
        except Exception as e:
            print(f"Warning: Could not clean up {collection_name}: {e}")


@pytest.fixture
def test_user(db, test_collection_prefix, cleanup_collections):
    """Create a test user in Firebase."""
    user_id = f"test_user_{datetime.now(timezone.utc).timestamp()}"
    collection_name = f"{test_collection_prefix}_users"
    cleanup_collections.append(collection_name)
    
    user_data = {
        "user_id": user_id,
        "email": f"{user_id}@test.com",
        "name": "Test User",
        "role": "Member",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Create user in Firestore
    db.collection(collection_name).document(user_id).set(user_data)
    
    yield {**user_data, "collection": collection_name}
    
    # Cleanup
    try:
        db.collection(collection_name).document(user_id).delete()
    except:
        pass


@pytest.fixture
def test_admin(db, test_collection_prefix, cleanup_collections):
    """Create a test admin user in Firebase."""
    user_id = f"test_admin_{datetime.now(timezone.utc).timestamp()}"
    collection_name = f"{test_collection_prefix}_users"
    cleanup_collections.append(collection_name)
    
    admin_data = {
        "user_id": user_id,
        "email": f"{user_id}@test.com",
        "name": "Test Admin",
        "role": "Admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Create admin in Firestore
    db.collection(collection_name).document(user_id).set(admin_data)
    
    yield {**admin_data, "collection": collection_name}
    
    # Cleanup
    try:
        db.collection(collection_name).document(user_id).delete()
    except:
        pass


@pytest.fixture
def test_project(db, test_user, test_collection_prefix, cleanup_collections):
    """Create a test project in Firebase."""
    project_id = f"test_project_{datetime.now(timezone.utc).timestamp()}"
    collection_name = f"{test_collection_prefix}_projects"
    cleanup_collections.append(collection_name)
    
    project_data = {
        "project_id": project_id,
        "name": "Test Project",
        "description": "A test project for integration testing",
        "created_by": {"user_id": test_user["user_id"], "email": test_user["email"]},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }
    
    db.collection(collection_name).document(project_id).set(project_data)
    
    yield {**project_data, "collection": collection_name}
    
    # Cleanup
    try:
        db.collection(collection_name).document(project_id).delete()
    except:
        pass


@pytest.fixture
def test_task(db, test_user, test_project, test_collection_prefix, cleanup_collections):
    """Create a test task in Firebase."""
    task_id = f"test_task_{datetime.now(timezone.utc).timestamp()}"
    collection_name = f"{test_collection_prefix}_tasks"
    cleanup_collections.append(collection_name)
    
    task_data = {
        "task_id": task_id,
        "title": "Test Task",
        "description": "A test task for integration testing",
        "status": "To Do",
        "priority": 5,
        "project_id": test_project["project_id"],
        "created_by": {"user_id": test_user["user_id"], "email": test_user["email"]},
        "assigned_to": None,
        "due_date": (datetime.now(timezone.utc)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_recurring": False,
        "labels": []
    }
    
    db.collection(collection_name).document(task_id).set(task_data)
    
    yield {**task_data, "collection": collection_name}
    
    # Cleanup
    try:
        db.collection(collection_name).document(task_id).delete()
    except:
        pass


@pytest.fixture
def auth_token(test_user):
    """Generate authentication token for test user."""
    try:
        # Lazy import to avoid loading Firebase at module level
        from firebase_admin import auth as firebase_auth
        
        # Create custom token for test user
        token = firebase_auth.create_custom_token(test_user["user_id"])
        return token.decode('utf-8') if isinstance(token, bytes) else token
    except Exception as e:
        # Return mock token if Firebase Auth fails
        return f"Bearer test_token_{test_user['user_id']}"


@pytest.fixture
def auth_headers(auth_token):
    """Create authentication headers for requests."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
