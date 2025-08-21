#!/usr/bin/env python3
"""
Script to initialize the database with all required tables
"""

import asyncio
import asyncpg
from datetime import datetime
import uuid

async def init_database():
    """Initialize database with all required tables"""
    
    conn = await asyncpg.connect('postgresql://postgres@postgres:5432/eventticketing')
    
    print("Creating database tables...")
    
    # Users table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS "user" (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            email VARCHAR UNIQUE NOT NULL,
            first_name VARCHAR,
            last_name VARCHAR,
            hashed_password VARCHAR NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_superuser BOOLEAN DEFAULT FALSE,
            role VARCHAR DEFAULT 'attendee',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Organizations table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS organization (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            name VARCHAR NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # User-Organization association table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS user_organization (
            user_id VARCHAR REFERENCES "user"(id) ON DELETE CASCADE,
            organization_id VARCHAR REFERENCES organization(id) ON DELETE CASCADE,
            role VARCHAR NOT NULL DEFAULT 'member',
            PRIMARY KEY (user_id, organization_id)
        )
    ''')
    
    # Events table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS event (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            title VARCHAR NOT NULL,
            description TEXT,
            start_datetime TIMESTAMP NOT NULL,
            end_datetime TIMESTAMP NOT NULL,
            venue_name VARCHAR,
            venue_address TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    print("✅ Database tables created successfully!")
    
    # Create admin user
    admin_id = str(uuid.uuid4())
    hashed_password = "$2b$12$vN8UYkbYGkC2Y9hO3N.MJeY8O9PYnV4z0Qc7.M5KYQxJ2Yx5Xx5Xx"  # AdminPass123
    
    try:
        await conn.execute('''
            INSERT INTO "user" (id, email, first_name, last_name, hashed_password, is_active, is_superuser, role)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''', admin_id, "admin@eventticketing.com", "System", "Administrator", hashed_password, True, True, "admin")
        
        print("✅ Default admin user created!")
        print(f"   Email: admin@eventticketing.com")
        print(f"   Password: AdminPass123")
        print(f"   User ID: {admin_id}")
        
    except asyncpg.UniqueViolationError:
        print("ℹ️  Admin user already exists!")
    
    await conn.close()
    print("✅ Database initialization complete!")

if __name__ == "__main__":
    asyncio.run(init_database())