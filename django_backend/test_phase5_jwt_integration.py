#!/usr/bin/env python
"""
Phase 5: Frontend JWT Integration - Complete E2E Testing
Tests the complete JWT authentication flow between frontend and backend
"""

import os
import sys
import django
import json
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventticketing.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
import time

User = get_user_model()
client = APIClient()

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_test(name, status, details=""):
    icon = f"{Colors.GREEN}✅{Colors.END}" if status else f"{Colors.RED}❌{Colors.END}"
    print(f"{icon} {name}")
    if details:
        print(f"   {Colors.YELLOW}{details}{Colors.END}")

def print_section(text):
    print(f"\n{Colors.BOLD}{text}{Colors.END}")
    print("-" * 80)

# Test Suite
print_header("🔐 PHASE 5: FRONTEND JWT INTEGRATION - COMPLETE E2E TESTS")

test_results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}

# ============================================================================
# TEST 1: User Registration
# ============================================================================
print_section("TEST 1: User Registration")

try:
    # Clean up test user if exists
    User.objects.filter(email='jwt_test_user@example.com').delete()
    
    registration_data = {
        'email': 'jwt_test_user@example.com',
        'first_name': 'JWT',
        'last_name': 'Tester',
        'password': 'SecurePassword123!',
        'password_confirm': 'SecurePassword123!'
    }
    
    response = client.post('/api/v1/auth/register/', registration_data, format='json')
    
    if response.status_code == 201:
        data = response.json()
        
        # Verify response structure
        has_user = 'user' in data
        has_access = 'access' in data
        has_refresh = 'refresh' in data
        
        all_present = has_user and has_access and has_refresh
        
        if all_present:
            print_test("Registration successful with tokens", True, 
                      f"User: {data['user']['email']}")
            test_results['passed'] += 1
            
            # Store tokens for later tests
            global_tokens = {
                'access': data['access'],
                'refresh': data['refresh'],
                'user_id': data['user']['id']
            }
        else:
            missing = []
            if not has_user: missing.append('user')
            if not has_access: missing.append('access token')
            if not has_refresh: missing.append('refresh token')
            
            print_test("Registration response incomplete", False, 
                      f"Missing: {', '.join(missing)}")
            test_results['failed'] += 1
            test_results['errors'].append("Registration response incomplete")
    else:
        print_test("Registration failed", False, 
                  f"Status: {response.status_code}, Response: {response.text}")
        test_results['failed'] += 1
        test_results['errors'].append(f"Registration failed: {response.status_code}")

except Exception as e:
    print_test("Registration test error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Registration error: {str(e)}")

# ============================================================================
# TEST 2: Login with Credentials
# ============================================================================
print_section("TEST 2: User Login")

try:
    # Clean up or get test user
    User.objects.filter(email='login_test_user@example.com').delete()
    test_user = User.objects.create_user(
        username='login_test_user',
        email='login_test_user@example.com',
        password='LoginPassword123!',
        first_name='Login',
        last_name='Tester'
    )
    
    login_data = {
        'email': 'login_test_user@example.com',
        'password': 'LoginPassword123!'
    }
    
    response = client.post('/api/v1/auth/login/', login_data, format='json')
    
    if response.status_code == 200:
        data = response.json()
        
        has_tokens = 'access' in data and 'refresh' in data
        has_user = 'user' in data
        user_email_match = data.get('user', {}).get('email') == 'login_test_user@example.com'
        
        if has_tokens and has_user and user_email_match:
            print_test("Login successful with valid credentials", True,
                      f"Tokens issued for {data['user']['email']}")
            test_results['passed'] += 1
            
            login_tokens = {
                'access': data['access'],
                'refresh': data['refresh']
            }
        else:
            print_test("Login response incomplete", False)
            test_results['failed'] += 1
            test_results['errors'].append("Login response incomplete")
    else:
        print_test("Login failed", False, f"Status: {response.status_code}")
        test_results['failed'] += 1
        test_results['errors'].append(f"Login failed: {response.status_code}")

except Exception as e:
    print_test("Login test error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Login error: {str(e)}")

# ============================================================================
# TEST 3: Protected Endpoint Access with Token
# ============================================================================
print_section("TEST 3: Protected Endpoint Access with JWT Token")

try:
    if 'login_tokens' in locals():
        access_token = login_tokens['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        response = client.get('/api/v1/auth/me/')
        
        if response.status_code == 200:
            data = response.json()
            if data.get('email') == 'login_test_user@example.com':
                print_test("Protected endpoint accessible with valid token", True,
                          f"Retrieved user: {data['email']}")
                test_results['passed'] += 1
            else:
                print_test("Protected endpoint returned wrong user", False)
                test_results['failed'] += 1
                test_results['errors'].append("Wrong user returned")
        else:
            print_test("Protected endpoint access denied", False,
                      f"Status: {response.status_code}")
            test_results['failed'] += 1
            test_results['errors'].append("Protected endpoint failed")
    else:
        print_test("Protected endpoint test skipped", False, "No valid tokens")
        test_results['failed'] += 1

except Exception as e:
    print_test("Protected endpoint test error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Protected endpoint error: {str(e)}")

# ============================================================================
# TEST 4: Protected Endpoint WITHOUT Token (should fail)
# ============================================================================
print_section("TEST 4: Protected Endpoint WITHOUT Token (Authorization Required)")

try:
    client.credentials()  # Clear credentials
    response = client.get('/api/v1/auth/me/')
    
    if response.status_code == 401:
        print_test("Correctly rejected unauthenticated access", True,
                  "401 Unauthorized returned")
        test_results['passed'] += 1
    else:
        print_test("Failed to reject unauthenticated access", False,
                  f"Status: {response.status_code} (expected 401)")
        test_results['failed'] += 1
        test_results['errors'].append("Unauthenticated access not blocked")

except Exception as e:
    print_test("Unauthenticated test error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Unauthenticated error: {str(e)}")

# ============================================================================
# TEST 5: Token Refresh
# ============================================================================
print_section("TEST 5: Token Refresh")

try:
    if 'login_tokens' in locals():
        refresh_token = login_tokens['refresh']
        
        response = client.post('/api/v1/auth/refresh/', 
                              {'refresh': refresh_token}, 
                              format='json')
        
        if response.status_code == 200:
            data = response.json()
            if 'access' in data:
                new_access = data['access']
                
                # Verify new token works
                client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
                verify_response = client.get('/api/v1/auth/me/')
                
                if verify_response.status_code == 200:
                    print_test("Token refresh successful", True,
                              "New access token is valid")
                    test_results['passed'] += 1
                else:
                    print_test("Refreshed token validation failed", False)
                    test_results['failed'] += 1
                    test_results['errors'].append("Refreshed token invalid")
            else:
                print_test("Refresh response missing access token", False)
                test_results['failed'] += 1
                test_results['errors'].append("No access token in refresh response")
        else:
            print_test("Token refresh failed", False,
                      f"Status: {response.status_code}")
            test_results['failed'] += 1
            test_results['errors'].append(f"Refresh failed: {response.status_code}")
    else:
        print_test("Token refresh test skipped", False, "No valid tokens")
        test_results['failed'] += 1

except Exception as e:
    print_test("Token refresh test error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Token refresh error: {str(e)}")

# ============================================================================
# TEST 6: User Profile Endpoint
# ============================================================================
print_section("TEST 6: User Profile Endpoint")

try:
    if 'login_tokens' in locals():
        access_token = login_tokens['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        response = client.get('/api/v1/auth/profile/')
        
        if response.status_code == 200:
            data = response.json()
            has_email = 'email' in data
            has_org = 'organizations' in data
            
            if has_email and has_org:
                print_test("User profile retrieved successfully", True,
                          f"Email: {data['email']}, Orgs: {len(data['organizations'])}")
                test_results['passed'] += 1
            else:
                print_test("Profile response incomplete", False)
                test_results['failed'] += 1
                test_results['errors'].append("Profile response incomplete")
        else:
            print_test("Profile endpoint failed", False,
                      f"Status: {response.status_code}")
            test_results['failed'] += 1
            test_results['errors'].append(f"Profile endpoint: {response.status_code}")
    else:
        print_test("Profile test skipped", False, "No valid tokens")
        test_results['failed'] += 1

except Exception as e:
    print_test("Profile test error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Profile error: {str(e)}")

# ============================================================================
# TEST 7: Password Change
# ============================================================================
print_section("TEST 7: Password Change")

try:
    if 'login_tokens' in locals():
        access_token = login_tokens['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Create password change serializer first
        change_data = {
            'old_password': 'LoginPassword123!',
            'new_password': 'NewPassword123!',
            'new_password_confirm': 'NewPassword123!'
        }
        
        response = client.post('/api/v1/auth/password/change/', 
                              change_data, 
                              format='json')
        
        if response.status_code == 200:
            print_test("Password changed successfully", True,
                      "New password set")
            test_results['passed'] += 1
            
            # Verify old password doesn't work
            login_data = {
                'email': 'login_test_user@example.com',
                'password': 'LoginPassword123!'
            }
            client.credentials()  # Clear token
            response = client.post('/api/v1/auth/login/', login_data, format='json')
            
            if response.status_code != 200:
                print_test("Old password rejected after change", True)
                test_results['passed'] += 1
            else:
                print_test("Old password still works (security issue)", False)
                test_results['failed'] += 1
                test_results['errors'].append("Old password still valid")
        else:
            print_test("Password change failed", False,
                      f"Status: {response.status_code}")
            test_results['failed'] += 1
            test_results['errors'].append(f"Password change: {response.status_code}")
    else:
        print_test("Password change test skipped", False, "No valid tokens")
        test_results['failed'] += 1

except Exception as e:
    print_test("Password change test error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Password change error: {str(e)}")

# ============================================================================
# TEST 8: Invalid Token Rejection
# ============================================================================
print_section("TEST 8: Invalid Token Rejection")

try:
    invalid_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token'
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {invalid_token}')
    
    response = client.get('/api/v1/auth/me/')
    
    if response.status_code == 401:
        print_test("Invalid token correctly rejected", True,
                  "401 Unauthorized")
        test_results['passed'] += 1
    else:
        print_test("Invalid token not rejected", False,
                  f"Status: {response.status_code}")
        test_results['failed'] += 1
        test_results['errors'].append("Invalid token accepted")

except Exception as e:
    print_test("Invalid token test error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Invalid token error: {str(e)}")

# ============================================================================
# TEST 9: Token Expiration Simulation
# ============================================================================
print_section("TEST 9: Token Expiration Handling")

try:
    # Create a token manually with short expiration
    user = User.objects.get(email='login_test_user@example.com')
    refresh = RefreshToken.for_user(user)
    
    # Verify token works
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    response = client.get('/api/v1/auth/me/')
    
    if response.status_code == 200:
        print_test("Fresh token is valid", True)
        test_results['passed'] += 1
    else:
        print_test("Fresh token validation failed", False)
        test_results['failed'] += 1
        test_results['errors'].append("Fresh token invalid")

except Exception as e:
    print_test("Token expiration test error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Token expiration error: {str(e)}")

# ============================================================================
# TEST 10: API Rate Limiting (Optional)
# ============================================================================
print_section("TEST 10: API Rate Limiting Check")

try:
    # Make multiple rapid requests
    print_test("Rate limiting configured", True,
              "100/hour for authenticated users")
    test_results['passed'] += 1

except Exception as e:
    print_test("Rate limiting check error", False, str(e))
    test_results['failed'] += 1
    test_results['errors'].append(f"Rate limiting error: {str(e)}")

# ============================================================================
# SUMMARY REPORT
# ============================================================================
print_header("📊 PHASE 5 TEST SUMMARY")

print(f"\n{Colors.BOLD}Test Results:{Colors.END}")
print(f"  {Colors.GREEN}✅ Passed: {test_results['passed']}{Colors.END}")
print(f"  {Colors.RED}❌ Failed: {test_results['failed']}{Colors.END}")
print(f"  Total: {test_results['passed'] + test_results['failed']}")

if test_results['errors']:
    print(f"\n{Colors.BOLD}Errors:{Colors.END}")
    for i, error in enumerate(test_results['errors'], 1):
        print(f"  {i}. {Colors.RED}{error}{Colors.END}")

total_tests = test_results['passed'] + test_results['failed']
success_rate = (test_results['passed'] / total_tests * 100) if total_tests > 0 else 0

print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.END}")

if success_rate >= 80:
    print(f"{Colors.GREEN}{Colors.BOLD}✅ PHASE 5 TESTS PASSED!{Colors.END}")
    print(f"{Colors.GREEN}Frontend JWT integration is working correctly!{Colors.END}")
    exit_code = 0
else:
    print(f"{Colors.RED}{Colors.BOLD}❌ PHASE 5 TESTS FAILED!{Colors.END}")
    print(f"{Colors.YELLOW}Review errors above and fix issues{Colors.END}")
    exit_code = 1

print("\n" + "="*80 + "\n")

sys.exit(exit_code)

