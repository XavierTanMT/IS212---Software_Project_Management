#!/usr/bin/env python3
"""
Setup script for IS212 Task Management Firebase Backend
This script helps configure Firebase and run the backend server
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header():
    print("=" * 60)
    print("IS212 Task Management - Firebase Backend Setup")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_environment():
    """Setup environment variables"""
    print("\n🔧 Setting up environment...")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("📝 Creating .env file from template...")
            with open(env_example, 'r') as f:
                content = f.read()
            with open(env_file, 'w') as f:
                f.write(content)
            print("✅ .env file created")
        else:
            print("⚠️  No .env.example found, creating basic .env file...")
            with open(env_file, 'w') as f:
                f.write("""FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
CORS_ORIGINS=http://localhost:5000,http://localhost:8000
""")
            print("✅ Basic .env file created")
    else:
        print("✅ .env file already exists")
    
    print("\n📋 Next steps:")
    print("1. Create a Firebase project at https://console.firebase.google.com/")
    print("2. Enable Firestore Database")
    print("3. Enable Authentication (Email/Password)")
    print("4. Generate a service account key:")
    print("   - Go to Project Settings > Service Accounts")
    print("   - Click 'Generate new private key'")
    print("   - Save as 'serviceAccountKey.json' in backend/ directory")
    print("5. Update FIREBASE_PROJECT_ID in .env file")
    print()

def check_firebase_config():
    """Check if Firebase is properly configured"""
    print("\n🔍 Checking Firebase configuration...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    project_id = os.getenv('FIREBASE_PROJECT_ID')
    credentials_path = os.getenv('FIREBASE_CREDENTIALS_PATH', './serviceAccountKey.json')
    
    if not project_id or project_id == 'your-project-id':
        print("❌ FIREBASE_PROJECT_ID not set in .env file")
        return False
    
    if not os.path.exists(credentials_path):
        print(f"❌ Firebase credentials file not found: {credentials_path}")
        return False
    
    print("✅ Firebase configuration looks good")
    return True

def test_firebase_connection():
    """Test Firebase connection"""
    print("\n🔗 Testing Firebase connection...")
    try:
        from config.firebase_config import firebase_config
        print("✅ Firebase connection successful")
        return True
    except Exception as e:
        print(f"❌ Firebase connection failed: {e}")
        return False

def run_server():
    """Run the Flask server"""
    print("\n🚀 Starting Flask server...")
    try:
        subprocess.run([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def main():
    print_header()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Check Firebase configuration
    if not check_firebase_config():
        print("\n⚠️  Please complete Firebase setup before running the server")
        print("Run this script again after configuring Firebase")
        sys.exit(1)
    
    # Test Firebase connection
    if not test_firebase_connection():
        print("\n⚠️  Firebase connection failed. Please check your configuration")
        sys.exit(1)
    
    print("\n🎉 Setup complete! Starting server...")
    print("Server will be available at: http://localhost:5000")
    print("API endpoints:")
    print("  - Health check: http://localhost:5000/api/health")
    print("  - Auth: http://localhost:5000/api/auth/*")
    print("  - Users: http://localhost:5000/api/users/*")
    print("  - Tasks: http://localhost:5000/api/tasks/*")
    print("  - Projects: http://localhost:5000/api/projects/*")
    print("\nPress Ctrl+C to stop the server")
    print()
    
    # Run server
    run_server()

if __name__ == "__main__":
    main()
