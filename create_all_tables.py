#!/usr/bin/env python3
"""
Script to create all missing database tables
"""

import asyncio
import asyncpg

async def create_all_tables():
    """Create all required database tables"""
    
    conn = await asyncpg.connect('postgresql://postgres@postgres:5432/eventticketing')
    
    print("Creating all database tables...")
    
    # Event Categories table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS event_category (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            name VARCHAR NOT NULL,
            description TEXT,
            color VARCHAR,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Event-Category association table (many-to-many)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS event_category_association (
            event_id VARCHAR REFERENCES event(id) ON DELETE CASCADE,
            event_category_id VARCHAR REFERENCES event_category(id) ON DELETE CASCADE,
            PRIMARY KEY (event_id, event_category_id)
        )
    ''')
    
    # Ticket Types table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS ticket_type (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            event_id VARCHAR REFERENCES event(id) ON DELETE CASCADE,
            name VARCHAR NOT NULL,
            description TEXT,
            price DECIMAL(10,2),
            quantity INTEGER,
            sold_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            sale_start TIMESTAMP,
            sale_end TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Price Tiers table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS price_tier (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            ticket_type_id VARCHAR REFERENCES ticket_type(id) ON DELETE CASCADE,
            name VARCHAR NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            quantity INTEGER,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Promo Codes table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS promo_code (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            event_id VARCHAR REFERENCES event(id) ON DELETE CASCADE,
            code VARCHAR UNIQUE NOT NULL,
            discount_type VARCHAR NOT NULL,
            discount_value DECIMAL(10,2),
            max_uses INTEGER,
            used_count INTEGER DEFAULT 0,
            valid_from TIMESTAMP,
            valid_until TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Orders table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS "order" (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            user_id VARCHAR REFERENCES "user"(id),
            event_id VARCHAR REFERENCES event(id),
            status VARCHAR NOT NULL DEFAULT 'pending',
            total_amount DECIMAL(10,2) NOT NULL,
            currency VARCHAR DEFAULT 'USD',
            payment_method VARCHAR,
            payment_status VARCHAR,
            payment_intent_id VARCHAR,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Order Items table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS order_item (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            order_id VARCHAR REFERENCES "order"(id) ON DELETE CASCADE,
            ticket_type_id VARCHAR REFERENCES ticket_type(id),
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            total_price DECIMAL(10,2) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Tickets table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS ticket (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            order_id VARCHAR REFERENCES "order"(id),
            ticket_type_id VARCHAR REFERENCES ticket_type(id),
            attendee_name VARCHAR,
            attendee_email VARCHAR,
            ticket_code VARCHAR UNIQUE,
            qr_code VARCHAR,
            is_checked_in BOOLEAN DEFAULT FALSE,
            checked_in_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Payments table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS payment (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            order_id VARCHAR REFERENCES "order"(id),
            stripe_payment_intent_id VARCHAR,
            amount DECIMAL(10,2) NOT NULL,
            currency VARCHAR DEFAULT 'USD',
            status VARCHAR NOT NULL,
            provider VARCHAR DEFAULT 'stripe',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Attendees table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS attendee (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            event_id VARCHAR REFERENCES event(id),
            user_id VARCHAR REFERENCES "user"(id),
            ticket_id VARCHAR REFERENCES ticket(id),
            first_name VARCHAR,
            last_name VARCHAR,
            email VARCHAR,
            phone VARCHAR,
            checked_in BOOLEAN DEFAULT FALSE,
            check_in_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Cart table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            user_id VARCHAR REFERENCES "user"(id),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Cart Items table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS cart_item (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
            cart_id VARCHAR REFERENCES cart(id) ON DELETE CASCADE,
            ticket_type_id VARCHAR REFERENCES ticket_type(id),
            quantity INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    print("✅ All database tables created successfully!")
    
    # Verify tables exist
    result = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    print(f"✅ Created {len(result)} tables:")
    for row in result:
        print(f"  - {row['tablename']}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(create_all_tables())