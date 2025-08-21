#!/usr/bin/env python3
"""
Script to create all enum types in PostgreSQL
"""

import asyncio
import asyncpg

async def create_enums():
    """Create all enum types"""
    
    conn = await asyncpg.connect('postgresql://postgres@postgres:5432/eventticketing')
    
    print("Creating enum types...")
    
    # User Role enum
    await conn.execute('''
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('ADMIN', 'ORGANIZER', 'ATTENDEE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    ''')
    
    # Event Status enum
    await conn.execute('''
        DO $$ BEGIN
            CREATE TYPE eventstatus AS ENUM ('DRAFT', 'PUBLISHED', 'CANCELLED', 'COMPLETED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    ''')
    
    # Order Status enum
    await conn.execute('''
        DO $$ BEGIN
            CREATE TYPE orderstatus AS ENUM ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED', 'REFUNDED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    ''')
    
    # Payment Method enum
    await conn.execute('''
        DO $$ BEGIN
            CREATE TYPE paymentmethod AS ENUM ('STRIPE', 'PAYPAL', 'CASH', 'BANK_TRANSFER');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    ''')
    
    # Payment Status enum
    await conn.execute('''
        DO $$ BEGIN
            CREATE TYPE paymentstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', 'REFUNDED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    ''')
    
    # Payment Provider enum
    await conn.execute('''
        DO $$ BEGIN
            CREATE TYPE paymentprovider AS ENUM ('STRIPE', 'PAYPAL', 'SQUARE', 'MANUAL');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    ''')
    
    # Discount Type enum
    await conn.execute('''
        DO $$ BEGIN
            CREATE TYPE discounttype AS ENUM ('PERCENTAGE', 'FIXED', 'FREE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    ''')
    
    # Refund Status enum
    await conn.execute('''
        DO $$ BEGIN
            CREATE TYPE refundstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    ''')
    
    print("✅ All enum types created successfully!")
    
    # Update user table to use the enum
    await conn.execute('''
        ALTER TABLE "user" ALTER COLUMN role TYPE userrole USING role::userrole;
    ''')
    
    print("✅ User table updated to use enum!")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(create_enums())