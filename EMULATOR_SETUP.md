# Firebase Emulator Setup Guide

## 👋 Welcome New Team Members!

This guide will help you set up and use Firebase Emulators for local development. Don't worry if you're new to Firebase - we'll walk through everything step by step!

## 🤔 Why Use Emulators?

**The Problem:**
- Firebase cloud services have daily quota limits
- When exceeded, you get **Error 429** (Too Many Requests)
- This blocks your API calls and stops your development work
- Quota resets daily, but waiting is frustrating

**The Solution:**
- **Firebase Emulators** run entirely on your local machine
- ✅ **Unlimited API calls** - no quota limits
- ✅ **100% Free** - no charges ever
- ✅ **Works offline** - no internet needed
- ✅ **Faster** - no network latency
- ✅ **Safe** - changes don't affect production data
- ✅ **Easy to inspect** - built-in UI to view your data

Think of emulators as your personal Firebase playground!

Think of emulators as your personal Firebase playground!

---

## 📋 Prerequisites (One-Time Setup)

Before starting, make sure you have:

- [x] **Node.js** installed (version 14 or higher)
  - Check: `node --version`
  - Download: https://nodejs.org/

- [x] **Firebase CLI** installed
  - Check: `firebase --version`
  - Install: `npm install -g firebase-tools`

- [x] **Python 3.11+** installed
  - Check: `python --version`
  - This project requires Python 3.11 or higher

- [x] **Project dependencies** installed
  - Run: `pip install -r backend/requirements.txt`

**✅ First time?** Run these commands to get set up:

```bash
# Install Firebase CLI globally
npm install -g firebase-tools

# Install Python dependencies
pip install -r backend/requirements.txt
```

---

## 🚀 Quick Start (Every Development Session)

### Step 1: Start Firebase Emulators

Open your **first terminal** and run:

```bash
firebase emulators:start
```

**What you'll see:**
```
┌─────────────────────────────────────────────────────────────┐
│ ✔  All emulators ready! It is now safe to connect your app. │
│ i  View Emulator UI at http://localhost:4000               │
└─────────────────────────────────────────────────────────────┘

┌────────────┬────────────────┬─────────────────────────────────┐
│ Emulator   │ Host:Port      │ View in Emulator UI             │
├────────────┼────────────────┼─────────────────────────────────┤
│ Auth       │ localhost:9099 │ http://localhost:4000/auth      │
│ Firestore  │ localhost:8080 │ http://localhost:4000/firestore │
└────────────┴────────────────┴─────────────────────────────────┘
```

✅ **Leave this terminal running!** Don't close it - the emulators need to stay active.

💡 **Pro Tip:** Open the Emulator UI at http://localhost:4000 in your browser to see your data in real-time!

---

### Step 2: Start Backend with Emulators

Open a **second terminal** and choose your method:

#### Option A: Using PowerShell (Recommended for Windows)

```powershell
#### Option A: Using PowerShell (Recommended for Windows)

```powershell
# Set emulator environment variables
$env:FIRESTORE_EMULATOR_HOST="localhost:8080"
$env:FIREBASE_AUTH_EMULATOR_HOST="localhost:9099"
$env:GCLOUD_PROJECT="demo-test-project"
$env:GOOGLE_APPLICATION_CREDENTIALS="tests\integration\dummy-credentials.json"

# Navigate to backend and start
cd backend
python app.py
```

#### Option B: Using Command Prompt (Windows)

```cmd
# Set emulator environment variables
set FIRESTORE_EMULATOR_HOST=localhost:8080
set FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
set GCLOUD_PROJECT=demo-test-project
set GOOGLE_APPLICATION_CREDENTIALS=tests\integration\dummy-credentials.json

# Navigate to backend and start
cd backend
python app.py
```

#### Option C: Using Batch Script (Easiest!)

If you don't want to type all those commands, just run:

```cmd
start_backend_with_emulators.bat
```

> ⚠️ **Note:** PowerShell users might get a security error. Use Command Prompt or Option A/B instead.

---

### Step 3: Verify Everything is Working

**What you should see in Terminal 2:**

```
🔥 Firebase Emulator Mode Detected
   ✓ Firestore Emulator: localhost:8080
   ✓ Auth Emulator: localhost:9099
   ✓ Set GCLOUD_PROJECT=demo-test-project
   ✓ Using dummy credentials for emulator
   ✓ Firebase initialized for EMULATOR use
   ⚠️  Using emulators - NO CLOUD QUOTA USED

 * Running on http://127.0.0.1:5000
```

✅ **Success!** You're now running in emulator mode!

✅ **Success!** You're now running in emulator mode!

**Test your setup:**

Open a third terminal and try creating a user:

```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"test1\",\"email\":\"test@example.com\",\"name\":\"Test User\"}"
```

Then check the Emulator UI at http://localhost:4000/firestore to see your new user!

---

## 🎯 Daily Development Workflow

Once you're set up, here's your daily routine:

1. **Morning:** Start emulators in Terminal 1
   ```bash
   firebase emulators:start
   ```

2. **Start backend** in Terminal 2
   ```bash
   # Set env vars (PowerShell)
   $env:FIRESTORE_EMULATOR_HOST="localhost:8080"
   $env:FIREBASE_AUTH_EMULATOR_HOST="localhost:9099"
   $env:GCLOUD_PROJECT="demo-test-project"
   $env:GOOGLE_APPLICATION_CREDENTIALS="tests\integration\dummy-credentials.json"
   cd backend
   python app.py
   ```

3. **Develop!** Make API calls, run tests, build features

4. **End of day:** Press `Ctrl+C` in both terminals to stop

💡 **Pro Tip:** Keep the Emulator UI open in a browser tab to monitor your data changes in real-time!

---

## 🔍 Understanding the Emulator UI

Visit **http://localhost:4000** to access the Firebase Emulator Suite UI.

### What You Can Do:

**📁 Firestore Tab:**
- View all collections and documents
- See data structure and values
- Manually add/edit/delete documents
- Export data to save your test data

**👤 Authentication Tab:**
- See all created users
- View user IDs and emails
- Create test users manually
- Clear all users quickly

**📊 Logs Tab:**
- Monitor API calls in real-time
- Debug errors and see stack traces
- Filter by emulator type

**⬇️ Import/Export:**
- Save your emulator data
- Load it back later
- Share test data with team

---

## 🧪 Running Tests with Emulators

### Integration Tests (Automatically Use Emulators)

```bash
# Run all integration tests - uses emulators automatically
python -m pytest tests/integration

# Run specific test file
python -m pytest tests/integration/test_users_coverage.py

# Run with coverage report
python -m pytest tests/integration --cov=backend --cov-report=term
```

✅ **No quota consumed!** Integration tests automatically detect and use emulators.

### Unit Tests (Don't Need Emulators)

```bash
# Unit tests use mocks, not emulators
python -m pytest tests/unit
```

---

## 💾 Saving Your Test Data (Data Persistence)

By default, emulator data is **deleted when you stop the emulators**. To keep your data:

### Save Data on Exit

```bash
firebase emulators:start --export-on-exit=./emulator-data
```

### Load Saved Data on Start

```bash
firebase emulators:start --import=./emulator-data --export-on-exit=./emulator-data
```

This creates a `emulator-data/` folder with your saved Firestore collections and Auth users.

**Use Case:** 
- Create test users once
- Save them with `--export-on-exit`
- Load them every time with `--import`
- Skip manual user creation!

---

## 🔄 Switching Between Cloud and Emulator

### Use Emulators (Development)

Set these environment variables before starting backend:

```bash
FIRESTORE_EMULATOR_HOST=localhost:8080
FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
```

You'll see: `🔥 Firebase Emulator Mode Detected`

### Use Cloud Firebase (Production/Deployment)

Don't set any emulator variables. Just run:

```bash
cd backend
python app.py
```

You'll see: `✓ Firebase initialized successfully (CLOUD MODE)`

⚠️ **Warning:** Cloud mode consumes quota. Use emulators for development!

---

## ❓ Troubleshooting Common Issues

### ❌ "Connection refused" or "ECONNREFUSED"

**Problem:** Backend can't connect to emulators

**Solutions:**
1. Make sure emulators are running first
   ```bash
   firebase emulators:start
   ```
2. Check emulators are on correct ports (8080, 9099)
3. Verify environment variables are set correctly

---

### ❌ "Port already in use"

**Problem:** Another process is using ports 8080, 9099, or 4000

**Solutions:**
1. Stop other Firebase emulators
2. Kill processes using those ports:
   ```bash
   # Find process using port 8080
   netstat -ano | findstr :8080
   # Kill it (replace PID)
   taskkill /PID <process_id> /F
   ```
3. Or change ports in `firebase.json`

---

### ❌ "Firebase initialization failed"

**Problem:** Missing or invalid credentials file

**Solutions:**
1. Check file exists:
   ```bash
   dir tests\integration\dummy-credentials.json
   ```
2. If missing, it should be in the repo. Pull latest code:
   ```bash
   git pull
   ```
3. Verify environment variable points to correct path

---

### ❌ "Module not found" errors

**Problem:** Python dependencies not installed

**Solution:**
```bash
pip install -r backend/requirements.txt
```

---

### ❌ PowerShell script won't run

**Problem:** Execution policy blocks scripts

**Solutions:**
1. Use Command Prompt instead, or
2. Use manual commands (Option A in Step 2), or
3. Change execution policy (requires admin):
   ```powershell
   Set-ExecutionPolicy RemoteSigned
   ```

---

## 📚 Learning Resources

### Official Documentation
- [Firebase Emulator Suite](https://firebase.google.com/docs/emulator-suite)
- [Local Emulator Suite UI](https://firebase.google.com/docs/emulator-suite/connect_and_prototype)

### Project Files
- `firebase.json` - Emulator port configuration
- `tests/integration/dummy-credentials.json` - Fake credentials for emulator
- `backend/app.py` - Backend initialization with emulator detection
- `tests/integration/conftest.py` - Test configuration for emulators

---

## 🆘 Getting Help

**Still stuck?**

1. Check this guide again - solution is usually here!
2. Ask in team chat with:
   - What you tried
   - Error message (full text)
   - Screenshots of terminal output
3. Check if emulators are running: http://localhost:4000

**Common checks:**
- [ ] Emulators running? `firebase emulators:start`
- [ ] Environment variables set? Check with `echo $env:FIRESTORE_EMULATOR_HOST`
- [ ] In correct directory? Should be in project root
- [ ] Dependencies installed? `pip list | findstr firebase`

---

## ✨ Pro Tips for New Members

1. **Keep Emulator UI open** - Watch your data change in real-time
2. **Use data persistence** - Save time by keeping test users
3. **Check the Logs tab** - Great for debugging API calls
4. **Export test scenarios** - Save interesting data states
5. **Emulators = Safe space** - Break things, learn, experiment!

---

## 📊 Emulator vs Cloud Comparison

| Feature | Emulators | Cloud Firebase |
|---------|-----------|----------------|
| **Quota** | Unlimited | Limited (daily) |
| **Cost** | Free | Free tier, then paid |
| **Speed** | Fast (local) | Slower (network) |
| **Internet** | Not needed | Required |
| **Data persistence** | Optional | Always saved |
| **Production data** | Separate | Real data |
| **Best for** | Development, testing | Production, deployment |

---

## 🎉 You're Ready!

You now know how to:
- ✅ Start Firebase emulators
- ✅ Run backend in emulator mode  
- ✅ Use the Emulator UI
- ✅ Run tests without quota
- ✅ Troubleshoot common issues

**Happy coding!** 🚀

Remember: Emulators are your friend. Use them for all development work to avoid quota limits and work faster!
