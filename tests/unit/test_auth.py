"""
Quick test script for Firebase Authentication
Tests login endpoint with email/password
"""
import requests
import json

BASE_URL = "http://localhost:5000"

print("=" * 60)
print("🧪 Firebase Authentication Test")
print("=" * 60)

# Test 1: Register a new user
print("\n1️⃣ Testing Registration...")
print("-" * 60)

register_data = {
    "user_id": "testuser001",
    "name": "Test User",
    "email": "testuser001@example.com",
    "password": "testpass123"
}

try:
    response = requests.post(
        f"{BASE_URL}/api/users/auth/register",
        json=register_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.ok:
        data = response.json()
        print("✅ Registration successful!")
        print(f"User ID: {data['user']['user_id']}")
        print(f"Email: {data['user']['email']}")
        print(f"Token received: {data['firebaseToken'][:50]}...")
    else:
        print(f"❌ Registration failed: {response.json().get('error')}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("⚠️ Make sure backend is running: python backend/app.py")

# Test 2: Login with correct password
print("\n2️⃣ Testing Login (Correct Password)...")
print("-" * 60)

login_data = {
    "email": "testuser001@example.com",
    "password": "testpass123"
}

try:
    response = requests.post(
        f"{BASE_URL}/api/users/auth/login",
        json=login_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.ok:
        data = response.json()
        print("✅ Login successful!")
        print(f"User ID: {data['user']['user_id']}")
        print(f"Email: {data['user']['email']}")
        print(f"Token received: {data['firebaseToken'][:50]}...")
    else:
        print(f"❌ Login failed: {response.json().get('error')}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Login with wrong password
print("\n3️⃣ Testing Login (Wrong Password)...")
print("-" * 60)

wrong_login_data = {
    "email": "testuser001@example.com",
    "password": "wrongpassword"
}

try:
    response = requests.post(
        f"{BASE_URL}/api/users/auth/login",
        json=wrong_login_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.ok:
        print("❌ SECURITY ISSUE: Login should have failed!")
    else:
        error_msg = response.json().get('error')
        print(f"✅ Login correctly rejected: {error_msg}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Login with non-existent email
print("\n4️⃣ Testing Login (Non-existent Email)...")
print("-" * 60)

fake_login_data = {
    "email": "notexist@example.com",
    "password": "anypassword"
}

try:
    response = requests.post(
        f"{BASE_URL}/api/users/auth/login",
        json=fake_login_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.ok:
        print("❌ SECURITY ISSUE: Login should have failed!")
    else:
        error_msg = response.json().get('error')
        print(f"✅ Login correctly rejected: {error_msg}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("🎯 Test Summary")
print("=" * 60)
print("✅ If all tests passed, your authentication is working correctly!")
print("✅ Password verification is enabled")
print("✅ Firebase Web API Key is configured")
print("\nNext steps:")
print("1. Open login.html in your browser")
print("2. Login with: testuser001@example.com / testpass123")
print("3. Should redirect to dashboard")
print("=" * 60)
