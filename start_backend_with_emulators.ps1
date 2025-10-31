# Start Backend with Firebase Emulators
# This script starts the Flask backend using Firebase emulators instead of cloud
# This avoids quota errors (Error 429) and is free to use

Write-Host "🔥 Starting Backend with Firebase Emulators..." -ForegroundColor Cyan
Write-Host ""

# Set environment variables for Firebase emulators
$env:FIRESTORE_EMULATOR_HOST = "localhost:8080"
$env:FIREBASE_AUTH_EMULATOR_HOST = "localhost:9099"
$env:GCLOUD_PROJECT = "demo-test-project"

# Path to dummy credentials (required by Firebase Admin SDK even for emulators)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dummyCredsPath = Join-Path $scriptDir "tests\integration\dummy-credentials.json"
$env:GOOGLE_APPLICATION_CREDENTIALS = $dummyCredsPath

Write-Host "✓ Firebase Emulator Configuration:" -ForegroundColor Green
Write-Host "  - Firestore: $env:FIRESTORE_EMULATOR_HOST" -ForegroundColor Gray
Write-Host "  - Auth: $env:FIREBASE_AUTH_EMULATOR_HOST" -ForegroundColor Gray
Write-Host "  - Project: $env:GCLOUD_PROJECT" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  IMPORTANT: Firebase emulators must be running!" -ForegroundColor Yellow
Write-Host "  Start emulators in another terminal with:" -ForegroundColor Yellow
Write-Host "  firebase emulators:start" -ForegroundColor Yellow
Write-Host ""
Write-Host "💡 Emulator UI: http://localhost:4000" -ForegroundColor Cyan
Write-Host ""

# Start the Flask backend
Write-Host "🚀 Starting Flask Backend..." -ForegroundColor Cyan
Set-Location backend
python app.py
