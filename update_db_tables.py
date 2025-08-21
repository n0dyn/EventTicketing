#!/usr/bin/env python3
"""
Script to create missing database tables for recurring events
"""

import asyncio
import asyncpg

async def create_recurring_tables():
    """Create recurring event tables"""
    
    conn = await asyncpg.connect('postgresql://postgres@postgres:5432/eventticketing')
    
    print("Creating recurring event tables...")
    
    # Recurrence Patterns table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS recurrence_patterns (
            id SERIAL PRIMARY KEY,
            recurrence_type VARCHAR NOT NULL,
            interval_count INTEGER DEFAULT 1,
            weekdays JSONB,
            month_day INTEGER,
            month_week INTEGER,
            month_weekday INTEGER,
            year_month INTEGER,
            year_day INTEGER,
            end_date DATE,
            occurrence_count INTEGER,
            exclude_dates JSONB,
            include_dates JSONB,
            timezone VARCHAR DEFAULT 'UTC',
            custom_rule TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Event Series table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS event_series (
            id SERIAL PRIMARY KEY,
            uuid UUID DEFAULT gen_random_uuid() UNIQUE,
            title VARCHAR NOT NULL,
            description TEXT,
            template_data JSONB,
            recurrence_pattern_id INTEGER REFERENCES recurrence_patterns(id),
            series_start_date DATE NOT NULL,
            series_end_date DATE,
            default_start_time TIME,
            default_end_time TIME,
            default_duration_minutes INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            auto_publish BOOLEAN DEFAULT FALSE,
            advance_days INTEGER DEFAULT 30,
            max_instances INTEGER DEFAULT 100,
            owner_id VARCHAR REFERENCES "user"(id),
            organization_id VARCHAR REFERENCES organization(id),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Event Instances table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS event_instances (
            id SERIAL PRIMARY KEY,
            event_id VARCHAR REFERENCES event(id),
            event_series_id INTEGER REFERENCES event_series(id),
            custom_title VARCHAR,
            custom_description TEXT,
            custom_location VARCHAR,
            custom_start_time TIMESTAMP,
            custom_end_time TIMESTAMP,
            is_cancelled BOOLEAN DEFAULT FALSE,
            cancellation_reason TEXT,
            custom_data JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    print("✅ Recurring event tables created successfully!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(create_recurring_tables())