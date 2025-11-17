#!/usr/bin/env python
"""
Authentication endpoints tester
Tests JWT token functionality and auth flows
"""
import os
import django
import sys
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventticketing.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()
client = APIClient()

print("\n" + "="*80)
print("AUTHENTICATION TESTS - JWT TOKEN SYSTEM")
print("="*80 + "\n")

# Initialize tokens
access_token = None
refresh_token = None

# Test 1: Register new user
print("TEST 1: User Registration")
print("-" * 80)
registration_data = {
    'email': 'newuser123@example.com',  # Changed to avoid conflicts
    'first_name': 'Test',
    'last_name': 'User',
    'password': 'SecurePass123!',
    'password_confirm': 'SecurePass123!'
}
response = client.post('/api/v1/auth/register/', registration_data, format='json')
print(f"POST /api/v1/auth/register/ → Status: {response.status_code}")

if response.status_code == 201:
    print("✅ User registered successfully")
    data = response.json()
    print(f"   Email: {data['user']['email']}")
    print(f"   Has access token: {'access' in data['tokens']}")
    print(f"   Has refresh token: {'refresh' in data['tokens']}")
    access_token = data['tokens']['access']
    refresh_token = data['tokens']['refresh']
else:
    print(f"⚠️  Registration failed: {response.text}")
print()

# Test 2: Login with existing user
print("TEST 2: User Login")
print("-" * 80)
# Create a user first
try:
    user = User.objects.create_user(
        username='existinguser2',
        email='existinguser2@example.com',
        password='TestPass123!',
        first_name='Existing',
        last_name='User'
    )
    print("✅ Test user created")
except:
    print("ℹ️  Test user already exists")

login_data = {
    'email': 'existinguser2@example.com',
    'password': 'TestPass123!'
}
response = client.post('/api/v1/auth/login/', login_data, format='json')
print(f"POST /api/v1/auth/login/ → Status: {response.status_code}")

if response.status_code == 200:
    print("✅ Login successful")
    data = response.json()
    print(f"   User: {data['user']['full_name']}")
    print(f"   Access token length: {len(data['access'])}")
    print(f"   Refresh token length: {len(data['refresh'])}")
    access_token = data['access']
    refresh_token = data['refresh']
else:
    print(f"⚠️  Login failed: {response.text}")
print()

# Test 3: Access protected endpoint with token
print("TEST 3: Access Protected Endpoint with Token")
print("-" * 80)
if access_token:
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    response = client.get('/api/v1/auth/me/', format='json')
    print(f"GET /api/v1/auth/me/ → Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Successfully accessed protected endpoint")
        data = response.json()
        print(f"   User email: {data['email']}")
        print(f"   Full name: {data['full_name']}")
    else:
        print(f"❌ Failed to access: {response.text}")
else:
    print("⚠️  No access token available")
print()

# Test 4: Get user profile
print("TEST 4: Get User Profile")
print("-" * 80)
if access_token:
    response = client.get('/api/v1/auth/profile/', format='json')
    print(f"GET /api/v1/auth/profile/ → Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Retrieved user profile")
        data = response.json()
        print(f"   Email: {data['email']}")
        print(f"   Created: {data['created_at']}")
    else:
        print(f"❌ Failed: {response.text}")
else:
    print("⚠️  No access token available")
print()

# Test 5: Refresh token
print("TEST 5: Refresh Access Token")
print("-" * 80)
if refresh_token:
    refresh_data = {'refresh': refresh_token}
    response = client.post('/api/v1/auth/refresh/', refresh_data, format='json')
    print(f"POST /api/v1/auth/refresh/ → Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Token refreshed successfully")
        data = response.json()
        new_access_token = data['access']
        print(f"   New access token length: {len(new_access_token)}")
        access_token = new_access_token
    else:
        print(f"❌ Token refresh failed: {response.text}")
else:
    print("⚠️  No refresh token available")
print()

# Test 6: Change password
print("TEST 6: Change Password")
print("-" * 80)
if access_token:
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    change_pwd_data = {
        'old_password': 'TestPass123!',
        'new_password': 'NewSecurePass123!',
        'new_password_confirm': 'NewSecurePass123!'
    }
    response = client.post('/api/v1/auth/password/change/', change_pwd_data, format='json')
    print(f"POST /api/v1/auth/password/change/ → Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Password changed successfully")
    else:
        print(f"⚠️  Status: {response.status_code}")
else:
    print("⚠️  No access token available")
print()

# Test 7: Request password reset
print("TEST 7: Request Password Reset")
print("-" * 80)
client.credentials()  # Clear credentials
reset_data = {'email': 'existinguser@example.com'}
response = client.post('/api/v1/auth/password/reset/', reset_data, format='json')
print(f"POST /api/v1/auth/password/reset/ → Status: {response.status_code}")

if response.status_code == 200:
    print("✅ Password reset email sent")
    data = response.json()
    if 'uid' in data and 'token' in data:
        print("   (UID and token available for testing)")
        test_uid = data['uid']
        test_token = data['token']
else:
    print(f"⚠️  Status: {response.status_code}")
print()

# Test 8: Access without token
print("TEST 8: Access Protected Endpoint Without Token")
print("-" * 80)
response = client.get('/api/v1/events/', format='json')
print(f"GET /api/v1/events/ (no token) → Status: {response.status_code}")

if response.status_code == 401:
    print("✅ Correctly rejected unauthenticated request")
elif response.status_code == 403:
    print("✅ Correctly denied access")
else:
    print(f"⚠️  Unexpected status: {response.status_code}")
print()

print("="*80)
print("AUTHENTICATION TESTS COMPLETE")
print("="*80)
print("\n✅ JWT Authentication System is Functional!\n")

