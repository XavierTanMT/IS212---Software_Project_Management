#!/usr/bin/env python3
"""
Start Firebase emulators for integration testing.
This script checks if Firebase CLI is installed and starts the emulators.
"""
import subprocess
import sys
import os
import time
import socket

def check_port(host, port):
    """Check if a port is already in use."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def check_firebase_cli():
    """Check if Firebase CLI is installed."""
    try:
        result = subprocess.run(
            ["firebase", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ Firebase CLI installed: {version}")
            return True
        else:
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def install_firebase_cli():
    """Provide instructions to install Firebase CLI."""
    print("\n" + "="*80)
    print("Firebase CLI not found. Please install it:")
    print("="*80)
    print("\nOption 1: Using npm (recommended)")
    print("  npm install -g firebase-tools")
    print("\nOption 2: Using standalone binary")
    print("  Visit: https://firebase.google.com/docs/cli#install-cli-windows")
    print("\nAfter installation, run this script again.")
    print("="*80)

def start_emulators():
    """Start Firebase emulators."""
    print("\n" + "="*80)
    print("Starting Firebase Emulators...")
    print("="*80)
    
    # Check if emulators are already running
    ports_to_check = {
        "Firestore": 8080,
        "Auth": 9099,
        "Emulator UI": 4000,
        "Emulator Hub": 4400
    }
    
    running_emulators = []
    for name, port in ports_to_check.items():
        if check_port("localhost", port):
            running_emulators.append(f"{name} (port {port})")
    
    if running_emulators:
        print("\n⚠ Warning: Some emulator ports are already in use:")
        for emulator in running_emulators:
            print(f"  - {emulator}")
        
        response = input("\nContinue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted.")
            return False
    
    print("\nStarting emulators...")
    print("  Firestore: http://localhost:8080")
    print("  Auth: http://localhost:9099")
    print("  Emulator UI: http://localhost:4000")
    print("\nPress Ctrl+C to stop the emulators")
    print("="*80 + "\n")
    
    try:
        # Start emulators
        subprocess.run(
            ["firebase", "emulators:start"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("Emulators stopped.")
        print("="*80)
    except Exception as e:
        print(f"\n✗ Error starting emulators: {e}")
        return False
    
    return True

def main():
    """Main entry point."""
    print("="*80)
    print("Firebase Emulator Starter for Integration Tests")
    print("="*80)
    
    # Check if Firebase CLI is installed
    if not check_firebase_cli():
        install_firebase_cli()
        sys.exit(1)
    
    # Start emulators
    success = start_emulators()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
