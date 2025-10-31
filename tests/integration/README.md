# Integration Tests

This directory contains integration tests that interact with Firebase services **via emulators**.

## 🚀 Quick Start

Integration tests are configured to use **Firebase Local Emulator Suite** by default. This means:
- ✅ No Firebase credentials needed
- ✅ No quota limits
- ✅ Faster tests
- ✅ Free forever
- ✅ Works offline

### Step 1: Install Firebase CLI (One-time)

```bash
npm install -g firebase-tools
```

### Step 2: Start Emulators

**Option A: Using PowerShell script (Windows)**
```powershell
.\start_emulators.ps1
```

**Option B: Using Python script (Cross-platform)**
```bash
python start_emulators.py
```

**Option C: Manual start**
```bash
firebase emulators:start
```

### Step 3: Run Tests (in a new terminal)

Tests will automatically detect and use the emulators:

```bash
# Run all integration tests
python -m pytest tests/integration --ignore=tests/integration/archive -v

# Run specific test file
python -m pytest tests/integration/test_user_workflows.py -v

# Run with coverage
python -m pytest tests/integration --ignore=tests/integration/archive --cov=backend --cov-branch
```

## How It Works

The integration tests are configured to:
1. **Automatically use emulators** when they're running (localhost:8080 for Firestore, localhost:9099 for Auth)
2. **Skip gracefully** if emulators are not running (with helpful error messages)
3. **Never hit quota limits** because emulators are unlimited

## Prerequisites

### Required
- **Node.js and npm** (for Firebase CLI)
- **Firebase CLI**: `npm install -g firebase-tools`

### Optional (for production Firebase testing)
- Firebase service account credentials (not needed for emulator testing)

### Option 1: Using Service Account JSON File (Recommended)

1. Download your Firebase service account key from the Firebase Console:
   - Go to Project Settings > Service Accounts
   - Click "Generate New Private Key"
   - Save the JSON file securely

2. Set the path to your service account file:
   ```bash
   # Linux/Mac
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/serviceAccountKey.json"
   
   # Windows (PowerShell)
   $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\serviceAccountKey.json"
   
   # Windows (CMD)
   set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\serviceAccountKey.json
   ```

### Option 2: Using Environment Variables

Set the `FIREBASE_CREDENTIALS_JSON` environment variable with the JSON content:

```bash
# Linux/Mac
export FIREBASE_CREDENTIALS_JSON='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'

# Windows (PowerShell) - Use single quotes
$env:FIREBASE_CREDENTIALS_JSON='{"type":"service_account",...}'
```

### Option 3: Using .env File

Create a `.env` file in the project root with:

```env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json
# OR
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}
```

## Running Integration Tests

### Run all integration tests (excluding archived tests):
```bash
python -m pytest tests/integration --ignore=tests/integration/archive -v
```

### Run specific test file:
```bash
python -m pytest tests/integration/test_user_workflows.py -v
```

### Run with coverage:
```bash
python -m pytest tests/integration --ignore=tests/integration/archive --cov=backend --cov-branch
```

### Skip integration tests if Firebase not configured:
Integration tests will automatically skip if Firebase credentials are not found.

## Test Behavior Without Credentials

If Firebase credentials are not configured:
- Integration tests will be **automatically skipped** with a clear message
- Unit tests will continue to run normally (they use mocks)
- No errors will be raised

## Troubleshooting

### Tests Skip with "Firebase credentials not configured"
- Verify your credentials file exists
- Check environment variables are set correctly
- Ensure the credentials file has valid JSON
- Verify the service account has proper permissions

### Connection Errors
- Check your internet connection
- Verify Firebase project is active
- Check if any firewall is blocking Firebase API

### Permission Errors
- Ensure service account has the following roles:
  - Firebase Admin SDK Administrator Service Agent
  - Cloud Datastore User (for Firestore)

## Test Structure

```
tests/integration/
├── conftest.py              # Shared fixtures and configuration
├── test_user_workflows.py   # User management integration tests
├── test_task_workflows.py   # Task management integration tests
├── test_project_workflows.py # Project management integration tests
├── test_api_coverage_boost.py # API coverage tests
├── test_final_coverage_boost.py # Additional coverage tests
└── archive/                 # Archived/deprecated tests (excluded from CI)
```

## Test Fixtures

Common fixtures available in all integration tests:

- `app` - Flask application instance
- `client` - Flask test client
- `db` - Firestore database client
- `test_user` - Pre-created test user
- `test_admin` - Pre-created test admin user
- `test_project` - Pre-created test project
- `test_task` - Pre-created test task
- `auth_token` - Authentication token for test user
- `auth_headers` - HTTP headers with authentication

## Cleanup

Integration tests automatically clean up created resources after each test using the `cleanup_collections` fixture.

## CI/CD Configuration

In CI/CD pipelines, set Firebase credentials as a secret environment variable:

```yaml
# GitHub Actions example
env:
  FIREBASE_CREDENTIALS_JSON: ${{ secrets.FIREBASE_CREDENTIALS_JSON }}
```

## Best Practices

1. **Use test prefixes**: All test data uses timestamps and prefixes to avoid collisions
2. **Clean up resources**: Use fixtures that automatically clean up after tests
3. **Isolate tests**: Each test should be independent and not rely on other tests
4. **Use realistic data**: Integration tests should use data similar to production
5. **Monitor costs**: Firebase has quotas - avoid creating excessive test data
