# Phase 6: Data Migration - Complete Guide

**Duration**: 2-3 days  
**Complexity**: High  
**Risk Level**: Medium (with backup/rollback)  
**Status**: Ready to Execute

---

## 📋 Data Migration Strategy

### Overview
Migrate all production data from FastAPI/SQLAlchemy backend to Django ORM while maintaining:
- ✅ Data integrity
- ✅ Referential constraints
- ✅ Audit trails
- ✅ Rollback capability

### Data Flow
```
FastAPI (SQLAlchemy)
       ↓
Migration Script
       ↓
Django ORM
       ↓
PostgreSQL (production)
```

---

## 📊 Data Entities to Migrate

| Entity | FastAPI Model | Django Model | Status |
|--------|---------------|--------------|--------|
| Users | `User` | `User` | Ready |
| Organizations | `Organization` | `Organization` | Ready |
| Events | `Event` | `Event` | Ready |
| Tickets | `TicketType` | `TicketType` | Ready |
| Orders | `Order` | `Order` | Ready |
| Payments | `Payment` | `Payment` | Ready |
| Attendees | `Attendee` | `Attendee` | Ready |

---

## 🚀 Phase 6A: Pre-Migration Setup

### 1. Environment Preparation

```bash
# Step 1: Ensure Django database is empty
cd django_backend
python manage.py flush --noinput

# Step 2: Run all Django migrations
python manage.py migrate --verbosity 2

# Step 3: Create migration backup directory
mkdir -p migration_backups
```

### 2. Database Connection Setup

Update migration script environment:

```bash
# Set FastAPI database URL
export FASTAPI_DATABASE_URL="sqlite:///./fastapi.db"
# or for PostgreSQL:
# export FASTAPI_DATABASE_URL="postgresql://user@localhost/eventticketingold"

# Set Django database (already configured in settings.py)
export DJANGO_DATABASE_URL="postgresql://user@localhost/eventticketing"
```

### 3. Verify Connections

```bash
# Test FastAPI database connection
python -c "
import sqlalchemy as sa
engine = sa.create_engine('sqlite:///./fastapi.db')
with engine.connect() as conn:
    print('✅ FastAPI DB connected')
"

# Test Django connection
python manage.py dbshell
```

---

## 🔄 Phase 6B: Migration Execution

### Step 1: Create Backup (CRITICAL)

```bash
python migration_script.py --backup
```

**Output**: `migration_backups/backup_YYYYMMDD_HHMMSS.json`

This creates a snapshot for rollback.

### Step 2: Run Migration

```bash
python migration_script.py --migrate
```

**Expected Output**:
```
2025-11-15 10:30:15 - INFO - STARTING DATA MIGRATION
2025-11-15 10:30:16 - INFO - Creating backup...
2025-11-15 10:30:17 - INFO - ✅ Backup created: migration_backups/backup_20251115_103017.json
2025-11-15 10:30:18 - INFO - Connecting to FastAPI database...
2025-11-15 10:30:19 - INFO - ✅ Connected to FastAPI database: sqlite:///./fastapi.db
2025-11-15 10:30:20 - INFO - Migrating users...
2025-11-15 10:30:22 - INFO - Found 145 users to migrate
2025-11-15 10:30:25 - INFO - Users migration complete: 145 success, 0 failed
...
```

### Step 3: Verify Migration

```bash
python migration_script.py --verify
```

**Expected Output**:
```
================================================================================
VERIFICATION REPORT
================================================================================
✅ Users: 145
✅ Organizations: 12
✅ Events: 87
✅ Tickets: 234
✅ Orders: 567
✅ Payments: 389
================================================================================
```

---

## ✅ Phase 6C: Post-Migration Validation

### 1. Data Integrity Checks

```python
# Check user migration
from django.contrib.auth import get_user_model
User = get_user_model()
print(f"Total users: {User.objects.count()}")
print(f"Active users: {User.objects.filter(is_active=True).count()}")

# Check for duplicates
from django.db.models import Count
duplicates = User.objects.values('email').annotate(
    count=Count('id')
).filter(count__gt=1)
print(f"Email duplicates: {duplicates.count()}")

# Check for orphaned records
from events.models import Event
orphaned_events = Event.objects.filter(owner__isnull=True)
print(f"Events without owner: {orphaned_events.count()}")
```

### 2. Referential Integrity

```bash
# Run Django checks
python manage.py check

# Check for constraint violations
python manage.py sqlsequencereset app1 app2 app3 | python manage.py dbshell
```

### 3. Data Sampling

```python
# Verify sample records
from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.first()
print(f"Sample user: {user.email}")
print(f"  Name: {user.first_name} {user.last_name}")
print(f"  Role: {user.role}")
print(f"  Active: {user.is_active}")

# Check user organizations
from accounts.models import UserOrganization
orgs = UserOrganization.objects.filter(user=user)
print(f"  Organizations: {orgs.count()}")
```

### 4. API Endpoint Testing

```bash
# Test user endpoints
curl -X GET http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer {token}"

# Test event endpoints
curl -X GET http://localhost:8000/api/v1/events/

# Test order endpoints
curl -X GET http://localhost:8000/api/v1/orders/ \
  -H "Authorization: Bearer {token}"
```

---

## 🔧 Phase 6D: Rollback Procedure

### If Migration Fails

```bash
# Option 1: Restore from backup (manual)
python manage.py flush --noinput
# Then manually restore from SQL dump

# Option 2: Revert and retry
python manage.py migrate zero  # Clear all migrations
git checkout HEAD -- migration_script.py
python migration_script.py --migrate
```

### Rollback Checklist

- [ ] Stop application
- [ ] Backup current database state
- [ ] Restore from pre-migration backup
- [ ] Verify data integrity
- [ ] Restart application
- [ ] Test critical features
- [ ] Review logs for issues

---

## 📈 Migration Monitoring

### Real-time Progress

```bash
# Terminal 1: Watch database size
watch 'du -sh django_backend/db.sqlite3'

# Terminal 2: Monitor Django logs
tail -f logs/django.log

# Terminal 3: Watch migration script
python migration_script.py --migrate | tee logs/migration.log
```

### Performance Optimization

```python
# Use batch operations
from django.db.models import bulk_create

users = []
for fastapi_user in fastapi_users:
    users.append(User(
        email=fastapi_user.email,
        # ... other fields
    ))

# Create all at once (faster)
User.objects.bulk_create(users, batch_size=1000)
```

---

## 🧪 Phase 6E: Testing After Migration

### Unit Tests

```python
# test_migration.py
from django.test import TestCase
from django.contrib.auth import get_user_model

class MigrationTests(TestCase):
    def test_user_count(self):
        User = get_user_model()
        self.assertGreater(User.objects.count(), 0)

    def test_user_data_integrity(self):
        User = get_user_model()
        user = User.objects.first()
        self.assertIsNotNone(user.email)
        self.assertTrue(user.email.count('@') == 1)

    def test_no_duplicate_emails(self):
        User = get_user_model()
        duplicates = User.objects.values('email').filter(
            email__in=User.objects.values('email').annotate(
                count=models.Count('id')
            ).filter(count__gt=1)
        )
        self.assertEqual(duplicates.count(), 0)
```

### Integration Tests

```bash
# Run full test suite
python manage.py test

# Test critical user journeys
python manage.py test accounts.tests.UserAuthenticationTests
python manage.py test events.tests.EventCRUDTests
python manage.py test orders.tests.OrderProcessTests
```

### Frontend Testing

```bash
# Test login with migrated user
npm test -- LoginPage

# Test dashboard with migrated data
npm test -- Dashboard

# E2E test
npm run test:e2e
```

---

## 📝 Migration Checklist

### Pre-Migration
- [ ] Create full database backup
- [ ] Notify stakeholders
- [ ] Schedule maintenance window
- [ ] Document current state
- [ ] Test rollback procedure
- [ ] Prepare monitoring

### During Migration
- [ ] Monitor system resources
- [ ] Check error logs continuously
- [ ] Verify network connectivity
- [ ] Monitor database size growth
- [ ] Track migration time

### Post-Migration
- [ ] Run verification checks
- [ ] Test critical features
- [ ] Monitor API responses
- [ ] Check database consistency
- [ ] Review audit logs
- [ ] Communicate completion

---

## ⚠️ Common Issues & Solutions

### Issue 1: Foreign Key Violations
```
Error: Duplicate key value violates unique constraint
```

**Solution**:
```python
# Check and fix duplicate IDs
User.objects.filter(id__isnull=True).delete()
User.objects.values('id').annotate(count=Count('id')).filter(count__gt=1)
```

### Issue 2: Encoding Errors
```
Error: UnicodeDecodeError: 'utf-8' codec can't decode
```

**Solution**:
```python
# Ensure UTF-8 encoding
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

### Issue 3: Missing Foreign Keys
```
Error: IntegrityError at /migration/ FOREIGN KEY constraint failed
```

**Solution**:
```python
# Migrate parent records first
migrate_users()  # Before organizations
migrate_organizations()  # Before events
```

---

## 📊 Success Metrics

### After Migration, Verify:

| Metric | Target | Check |
|--------|--------|-------|
| Data Completeness | 100% | `SELECT COUNT(*) FROM users;` |
| Referential Integrity | 0 errors | `python manage.py check --deploy` |
| API Responsiveness | <200ms | `curl -w "%{time_total}" ...` |
| User Authentication | 100% | Login test with each user |
| Orders Accuracy | 100% | Sum of order totals match |
| Payment Records | 100% | Payment count matches |

---

## 🎯 Phase 6 Completion Criteria

✅ **Required**:
- [ ] All user data migrated
- [ ] All organizations migrated
- [ ] All events migrated
- [ ] Foreign key integrity verified
- [ ] No data loss
- [ ] API tests passing
- [ ] Frontend tests passing
- [ ] Rollback procedure tested

✅ **Optional**:
- [ ] Performance optimized
- [ ] Audit logs complete
- [ ] Migration report generated

---

## 📞 Support & Troubleshooting

### Emergency Contact
If migration fails:
1. Stop the application immediately
2. Check logs: `tail -f logs/migration.log`
3. Run rollback: `python migration_script.py --rollback`
4. Restore from backup if needed
5. Review errors and retry

### Common Commands

```bash
# View migration status
python manage.py showmigrations

# Clear migrations
python manage.py migrate zero

# Restart migrations
python manage.py migrate

# Check database
python manage.py dbshell
```

---

## 🎊 Summary

Phase 6 provides a **safe, tested data migration** from FastAPI to Django:

✅ Comprehensive backup & rollback  
✅ Data integrity validation  
✅ Error handling & recovery  
✅ Post-migration testing  
✅ Monitoring & logging  

**Ready to execute when you're ready!**

---

**Next Phase**: Phase 7 - Deployment  
**Current Progress**: 50% → 55% (after data migration)

