# Start Firebase Emulators for Integration Testing
# This script starts the Firebase emulators and sets up the environment

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Firebase Emulator Setup for Integration Tests" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

# Check if Firebase CLI is installed
Write-Host "`nChecking for Firebase CLI..." -ForegroundColor Yellow
try {
    $version = firebase --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Firebase CLI installed: $version" -ForegroundColor Green
    } else {
        throw "Firebase CLI not found"
    }
} catch {
    Write-Host "✗ Firebase CLI not found" -ForegroundColor Red
    Write-Host "`nPlease install Firebase CLI:" -ForegroundColor Yellow
    Write-Host "  npm install -g firebase-tools" -ForegroundColor White
    Write-Host "`nOr download from: https://firebase.google.com/docs/cli" -ForegroundColor White
    exit 1
}

# Check if emulators are already running
Write-Host "`nChecking if emulators are already running..." -ForegroundColor Yellow
$ports = @{
    "Firestore" = 8080
    "Auth" = 9099
    "UI" = 4000
    "Hub" = 4400
}

$running = @()
foreach ($service in $ports.Keys) {
    $port = $ports[$service]
    $connection = Test-NetConnection -ComputerName localhost -Port $port -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($connection) {
        $running += "$service (port $port)"
    }
}

if ($running.Count -gt 0) {
    Write-Host "`n⚠ Warning: Some emulator ports are already in use:" -ForegroundColor Yellow
    foreach ($item in $running) {
        Write-Host "  - $item" -ForegroundColor Yellow
    }
    $continue = Read-Host "`nContinue anyway? (y/N)"
    if ($continue -ne "y") {
        Write-Host "Aborted." -ForegroundColor Red
        exit 0
    }
}

# Start emulators
Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host "Starting Firebase Emulators..." -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "`nEmulator endpoints:" -ForegroundColor Yellow
Write-Host "  Firestore:    http://localhost:8080" -ForegroundColor White
Write-Host "  Auth:         http://localhost:9099" -ForegroundColor White
Write-Host "  Emulator UI:  http://localhost:4000" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop the emulators" -ForegroundColor Yellow
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

try {
    firebase emulators:start
} catch {
    Write-Host "`n✗ Error starting emulators: $_" -ForegroundColor Red
    exit 1
}
