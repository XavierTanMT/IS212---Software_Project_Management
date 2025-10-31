@echo off
REM Start Backend with Firebase Emulators
REM This script starts the Flask backend using Firebase emulators instead of cloud
REM This avoids quota errors (Error 429) and is free to use

echo.
echo =============================================================================
echo   Starting Backend with Firebase Emulators
echo =============================================================================
echo.

REM Set environment variables for Firebase emulators
set FIRESTORE_EMULATOR_HOST=localhost:8080
set FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
set GCLOUD_PROJECT=demo-test-project

REM Path to dummy credentials (required by Firebase Admin SDK even for emulators)
set GOOGLE_APPLICATION_CREDENTIALS=%~dp0tests\integration\dummy-credentials.json

echo [OK] Firebase Emulator Configuration:
echo   - Firestore: %FIRESTORE_EMULATOR_HOST%
echo   - Auth: %FIREBASE_AUTH_EMULATOR_HOST%
echo   - Project: %GCLOUD_PROJECT%
echo.
echo [!] IMPORTANT: Firebase emulators must be running!
echo     Start emulators in another terminal with:
echo     firebase emulators:start
echo.
echo [i] Emulator UI: http://localhost:4000
echo.

REM Start the Flask backend
echo [*] Starting Flask Backend...
cd backend
python app.py
