import sys
import types
import os

# Ensure repo root is on sys.path so local packages like `api` can be imported
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Also add backend dir to sys.path so `import api` (used inside backend.app) resolves
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Inject a fake firebase_admin and firebase_admin.credentials before importing
# so importing backend.app doesn't fail when firebase_admin isn't installed.
fake_firebase = types.ModuleType("firebase_admin")
fake_firebase._apps = []

fake_credentials = types.ModuleType("firebase_admin.credentials")
def _dummy_certificate(path):
    class _C: pass
    return _C()

fake_credentials.Certificate = _dummy_certificate
fake_firebase.credentials = fake_credentials
fake_firebase.initialize_app = lambda cred: None

# Provide a fake firestore module with a client() callable so imports succeed
fake_firestore = types.ModuleType("firebase_admin.firestore")
def _fake_client():
    # Return a minimal sentinel object; tests shouldn't call it during import
    return object()

fake_firestore.client = _fake_client
fake_firebase.firestore = fake_firestore

sys.modules["firebase_admin.firestore"] = fake_firestore

sys.modules["firebase_admin"] = fake_firebase
sys.modules["firebase_admin.credentials"] = fake_credentials

from backend import app as app_module


def test_health_endpoint(monkeypatch):
    """Ensure the Flask health endpoint returns OK without initializing Firebase."""
    # Prevent external Firebase initialization during tests
    monkeypatch.setattr(app_module, "init_firebase", lambda: None)

    app = app_module.create_app()
    client = app.test_client()

    resp = client.get("/")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert "service" in data
