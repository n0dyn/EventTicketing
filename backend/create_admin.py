#!/usr/bin/env python3
"""
Script to create a default admin user for the EventTicketing system
"""

import asyncio
import requests
import json

async def create_admin():
    """Create default admin user"""
    
    # Admin user data
    admin_data = {
        "email": "admin@eventticketing.com",
        "password": "AdminPass123",
        "first_name": "System",
        "last_name": "Administrator",
        "is_superuser": True,
        "is_active": True
    }
    
    # API endpoint
    url = "http://localhost:8000/api/v1/auth/register"
    
    try:
        print("Creating default admin user...")
        
        # Make registration request
        response = requests.post(
            url,
            json=admin_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            print("✅ Admin user created successfully!")
            print(f"   Email: {admin_data['email']}")
            print(f"   Password: {admin_data['password']}")
            print(f"   User ID: {user_data.get('id')}")
            print(f"   Is Superuser: {user_data.get('is_superuser')}")
            return True
        elif response.status_code == 400:
            error_detail = response.json().get("detail", "Unknown error")
            if "already exists" in str(error_detail):
                print("ℹ️  Admin user already exists!")
                print(f"   Email: {admin_data['email']}")
                print(f"   Password: {admin_data['password']}")
                return True
            else:
                print(f"❌ Failed to create admin user: {error_detail}")
                return False
        else:
            print(f"❌ Failed to create admin user. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend API at http://localhost:8000")
        print("   Make sure the backend service is running with: docker-compose up -d backend")
        return False
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(create_admin())
    if success:
        print("\n🎉 Admin setup complete!")
        print("   You can now log in to the admin dashboard at:")
        print("   http://localhost:3000/admin")
    else:
        print("\n❌ Admin setup failed!")
        exit(1)