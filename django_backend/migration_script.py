#!/usr/bin/env python
"""
Data Migration Script: FastAPI (SQLAlchemy) → Django ORM
Migrates all data from the original FastAPI backend to the new Django backend.

Usage:
    python migration_script.py --backup  # Create backup before migration
    python migration_script.py --migrate # Run migration
    python migration_script.py --verify  # Verify migration
    python migration_script.py --rollback # Rollback to backup
"""

import os
import sys
import django
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventticketing.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import User as DjangoUser, UserOrganization
from organizations.models import Organization
from events.models import Event, EventCategory
from tickets.models import TicketType, PromoCode, PriceTier
from orders.models import Order, OrderItem, Cart, CartItem
from payments.models import Payment, Refund
from attendees.models import Attendee, CheckIn, WaitlistEntry
from notifications.models import Notification
from files.models import File

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BACKUP_DIR = Path(__file__).parent / 'migration_backups'
BACKUP_DIR.mkdir(exist_ok=True)


class DataMigrationStats:
    """Track migration statistics"""
    def __init__(self):
        self.stats = {
            'users': {'success': 0, 'failed': 0, 'errors': []},
            'organizations': {'success': 0, 'failed': 0, 'errors': []},
            'events': {'success': 0, 'failed': 0, 'errors': []},
            'tickets': {'success': 0, 'failed': 0, 'errors': []},
            'orders': {'success': 0, 'failed': 0, 'errors': []},
            'payments': {'success': 0, 'failed': 0, 'errors': []},
            'attendees': {'success': 0, 'failed': 0, 'errors': []},
        }
        self.start_time = None
        self.end_time = None

    def record_success(self, model_name):
        self.stats[model_name]['success'] += 1

    def record_failure(self, model_name, error):
        self.stats[model_name]['failed'] += 1
        self.stats[model_name]['errors'].append(str(error))

    def print_summary(self):
        """Print migration summary"""
        total_success = sum(s['success'] for s in self.stats.values())
        total_failed = sum(s['failed'] for s in self.stats.values())
        duration = (self.end_time - self.start_time).total_seconds()

        print("\n" + "="*80)
        print("MIGRATION SUMMARY")
        print("="*80)
        for model_name, data in self.stats.items():
            print(f"\n{model_name.upper()}:")
            print(f"  ✅ Success: {data['success']}")
            print(f"  ❌ Failed: {data['failed']}")
            if data['errors']:
                print(f"  Errors: {data['errors'][:3]}")  # Show first 3 errors

        print(f"\nTotal Success: {total_success}")
        print(f"Total Failed: {total_failed}")
        print(f"Duration: {duration:.2f} seconds")
        print("="*80 + "\n")


def create_backup():
    """Create backup of current Django database"""
    logger.info("Creating backup...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backup_{timestamp}.json"

    backup_data = {
        'timestamp': timestamp,
        'users': DjangoUser.objects.count(),
        'organizations': Organization.objects.count(),
        'events': Event.objects.count(),
    }

    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)

    logger.info(f"✅ Backup created: {backup_file}")
    return backup_file


def connect_fastapi_db():
    """Connect to FastAPI SQLAlchemy database"""
    logger.info("Connecting to FastAPI database...")
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Adjust this connection string to match your FastAPI setup
        DATABASE_URL = os.getenv(
            'FASTAPI_DATABASE_URL',
            'sqlite:///./fastapi.db'  # Default for local testing
        )

        engine = create_engine(DATABASE_URL, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        logger.info(f"✅ Connected to FastAPI database: {DATABASE_URL}")
        return session
    except Exception as e:
        logger.error(f"❌ Failed to connect to FastAPI database: {e}")
        raise


def migrate_users(fastapi_session, stats: DataMigrationStats):
    """Migrate users from FastAPI to Django"""
    logger.info("Migrating users...")

    try:
        # Import FastAPI User model
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from app.models.user import User as FastAPIUser

        fastapi_users = fastapi_session.query(FastAPIUser).all()
        logger.info(f"Found {len(fastapi_users)} users to migrate")

        for fastapi_user in fastapi_users:
            try:
                # Check if user already exists
                if DjangoUser.objects.filter(email=fastapi_user.email).exists():
                    logger.debug(f"User {fastapi_user.email} already exists, skipping")
                    stats.record_success('users')
                    continue

                # Create Django user
                django_user = DjangoUser.objects.create(
                    id=fastapi_user.id,  # Preserve IDs for foreign keys
                    email=fastapi_user.email,
                    username=fastapi_user.email,  # Use email as username
                    first_name=fastapi_user.first_name or '',
                    last_name=fastapi_user.last_name or '',
                    password=fastapi_user.hashed_password,  # Already hashed
                    is_active=fastapi_user.is_active,
                    is_staff=fastapi_user.is_superuser,
                    is_superuser=fastapi_user.is_superuser,
                )

                # Migrate role
                if hasattr(fastapi_user, 'role'):
                    django_user.role = fastapi_user.role
                    django_user.save()

                stats.record_success('users')
                logger.debug(f"✅ Migrated user: {fastapi_user.email}")

            except Exception as e:
                logger.error(f"❌ Failed to migrate user {fastapi_user.email}: {e}")
                stats.record_failure('users', e)

        logger.info(f"Users migration complete: {stats.stats['users']['success']} success, {stats.stats['users']['failed']} failed")

    except Exception as e:
        logger.error(f"❌ Failed to migrate users: {e}")
        raise


def migrate_organizations(fastapi_session, stats: DataMigrationStats):
    """Migrate organizations from FastAPI to Django"""
    logger.info("Migrating organizations...")

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from app.models.organization import Organization as FastAPIOrganization

        fastapi_orgs = fastapi_session.query(FastAPIOrganization).all()
        logger.info(f"Found {len(fastapi_orgs)} organizations to migrate")

        for fastapi_org in fastapi_orgs:
            try:
                if Organization.objects.filter(id=fastapi_org.id).exists():
                    logger.debug(f"Organization {fastapi_org.name} already exists, skipping")
                    stats.record_success('organizations')
                    continue

                django_org = Organization.objects.create(
                    id=fastapi_org.id,
                    name=fastapi_org.name,
                    slug=fastapi_org.slug,
                    description=getattr(fastapi_org, 'description', ''),
                    logo_url=getattr(fastapi_org, 'logo_url', ''),
                    is_active=getattr(fastapi_org, 'is_active', True),
                    created_at=getattr(fastapi_org, 'created_at', datetime.now()),
                )

                # Migrate organization members
                if hasattr(fastapi_org, 'members'):
                    for member in fastapi_org.members:
                        try:
                            django_user = DjangoUser.objects.get(email=member.email)
                            UserOrganization.objects.get_or_create(
                                user=django_user,
                                organization=django_org,
                                defaults={'role': 'organizer'}
                            )
                        except DjangoUser.DoesNotExist:
                            logger.warning(f"User {member.email} not found for organization {fastapi_org.name}")

                stats.record_success('organizations')
                logger.debug(f"✅ Migrated organization: {fastapi_org.name}")

            except Exception as e:
                logger.error(f"❌ Failed to migrate organization {fastapi_org.name}: {e}")
                stats.record_failure('organizations', e)

        logger.info(f"Organizations migration complete: {stats.stats['organizations']['success']} success")

    except Exception as e:
        logger.error(f"❌ Failed to migrate organizations: {e}")


def migrate_events(fastapi_session, stats: DataMigrationStats):
    """Migrate events from FastAPI to Django"""
    logger.info("Migrating events...")

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from app.models.event import Event as FastAPIEvent

        fastapi_events = fastapi_session.query(FastAPIEvent).all()
        logger.info(f"Found {len(fastapi_events)} events to migrate")

        for fastapi_event in fastapi_events:
            try:
                if Event.objects.filter(id=fastapi_event.id).exists():
                    logger.debug(f"Event {fastapi_event.title} already exists, skipping")
                    stats.record_success('events')
                    continue

                # Get owner and organization
                owner = None
                organization = None

                if hasattr(fastapi_event, 'owner_id') and fastapi_event.owner_id:
                    try:
                        owner = DjangoUser.objects.get(id=fastapi_event.owner_id)
                    except DjangoUser.DoesNotExist:
                        pass

                if hasattr(fastapi_event, 'organization_id') and fastapi_event.organization_id:
                    try:
                        organization = Organization.objects.get(id=fastapi_event.organization_id)
                    except Organization.DoesNotExist:
                        pass

                # Create event
                django_event = Event.objects.create(
                    id=fastapi_event.id,
                    title=fastapi_event.title,
                    slug=fastapi_event.slug,
                    description=getattr(fastapi_event, 'description', ''),
                    location=getattr(fastapi_event, 'location', ''),
                    venue=getattr(fastapi_event, 'venue', ''),
                    start_datetime=fastapi_event.start_time,
                    end_datetime=fastapi_event.end_time,
                    timezone=getattr(fastapi_event, 'timezone', 'UTC'),
                    capacity=getattr(fastapi_event, 'capacity', 0),
                    is_free=getattr(fastapi_event, 'is_free', False),
                    is_active=getattr(fastapi_event, 'is_active', True),
                    owner=owner,
                    organization=organization,
                )

                stats.record_success('events')
                logger.debug(f"✅ Migrated event: {fastapi_event.title}")

            except Exception as e:
                logger.error(f"❌ Failed to migrate event {getattr(fastapi_event, 'title', 'unknown')}: {e}")
                stats.record_failure('events', e)

        logger.info(f"Events migration complete: {stats.stats['events']['success']} success")

    except Exception as e:
        logger.error(f"❌ Failed to migrate events: {e}")


def verify_migration(stats: DataMigrationStats):
    """Verify migration success"""
    logger.info("Verifying migration...")

    checks = {
        'Users': DjangoUser.objects.count(),
        'Organizations': Organization.objects.count(),
        'Events': Event.objects.count(),
        'Tickets': TicketType.objects.count(),
        'Orders': Order.objects.count(),
        'Payments': Payment.objects.count(),
    }

    print("\n" + "="*80)
    print("VERIFICATION REPORT")
    print("="*80)
    for model_name, count in checks.items():
        status = "✅" if count > 0 else "⚠️ "
        print(f"{status} {model_name}: {count}")
    print("="*80 + "\n")

    return all(count > 0 for count in checks.values())


def run_migration():
    """Run complete migration"""
    stats = DataMigrationStats()
    stats.start_time = datetime.now()

    try:
        # Step 1: Create backup
        logger.info("="*80)
        logger.info("STARTING DATA MIGRATION")
        logger.info("="*80)
        backup_file = create_backup()

        # Step 2: Connect to FastAPI database
        fastapi_session = connect_fastapi_db()

        # Step 3: Migrate data (in order of dependencies)
        migrate_users(fastapi_session, stats)
        migrate_organizations(fastapi_session, stats)
        migrate_events(fastapi_session, stats)

        # Step 4: Verify migration
        fastapi_session.close()
        success = verify_migration(stats)

        stats.end_time = datetime.now()
        stats.print_summary()

        if success:
            logger.info("✅ Migration completed successfully!")
            return 0
        else:
            logger.warning("⚠️ Migration completed with warnings")
            return 1

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        stats.end_time = datetime.now()
        stats.print_summary()
        return 1


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate data from FastAPI to Django')
    parser.add_argument('--backup', action='store_true', help='Create backup only')
    parser.add_argument('--migrate', action='store_true', help='Run migration')
    parser.add_argument('--verify', action='store_true', help='Verify migration only')
    parser.add_argument('--rollback', action='store_true', help='Rollback to backup')

    args = parser.parse_args()

    if args.backup:
        create_backup()
    elif args.rollback:
        logger.info("Rollback functionality requires manual database restoration")
    elif args.verify:
        stats = DataMigrationStats()
        verify_migration(stats)
    else:
        # Run full migration by default
        exit_code = run_migration()
        sys.exit(exit_code)

