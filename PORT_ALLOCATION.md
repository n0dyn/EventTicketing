# EventTicketing Port Allocation & Conflict Analysis

## Remote Server: 10.147.19.100

### Current Services & Port Usage

```
PORT    SERVICE                              STATUS        CONFLICT?
────────────────────────────────────────────────────────────────────
22      SSH                                  LISTEN        ❌ No
53      DNS (localhost)                      LISTEN        ❌ No
5432    PostgreSQL (carehubconnect)          LISTEN        ❌ No (internal)
5435    PostgreSQL (n0dehunt3r)              LISTEN        ✅ Used by other service
5678    n8n Workflow                         LISTEN        ❌ No
6379    Redis (carehubconnect/docker)        LISTEN        ❌ No (internal)
6380    Redis (n0dehunt3r)                   LISTEN        ✅ Used by other service
8000    carehubconnect-web                   LISTEN        ✅ Used by other service
8001    [AVAILABLE]                          FREE          ✅ Available
8081    n0dehunt3r-app                       LISTEN        ✅ Used by other service
9993    Zerotier                             LISTEN        ❌ No
────────────────────────────────────────────────────────────────────
```

### EventTicketing Port Allocation (CONFLICT-FREE)

```
SERVICE              PORT    MAPPING              STATUS       REASON
──────────────────────────────────────────────────────────────────────
PostgreSQL           5436    5436:5432            ✅ SAFE      Port 5432/5435 in use
Redis                6381    6381:6379            ✅ SAFE      Port 6379/6380 in use
Django Web           8002    8002:8000            ✅ SAFE      Port 8000/8001 in use
Nginx (HTTP)         9080    9080:80              ✅ SAFE      Standard alt port
Nginx (HTTPS)        9443    9443:443             ✅ SAFE      Standard alt port
Celery Worker        N/A     Internal only        ✅ SAFE      No external port
Celery Beat          N/A     Internal only        ✅ SAFE      No external port
──────────────────────────────────────────────────────────────────────
```

## Summary

✅ **NO PORT CONFLICTS DETECTED**

All allocated ports are available and don't conflict with existing services:
- ✅ PostgreSQL on 5436 (vs used 5432, 5435)
- ✅ Redis on 6381 (vs used 6379, 6380)
- ✅ Django on 8002 (vs used 8000, 8001)
- ✅ Nginx on 9080 (vs used 5678, 8081)
- ✅ Nginx SSL on 9443 (vs used all lower ports)

## Access URLs

**After Deployment:**
- **HTTP:** http://10.147.19.100:9080
- **HTTPS:** https://10.147.19.100:9443
- **API:** http://10.147.19.100:9080/api/v1/

## Environment Variables

Create `.env.production` on the deployment server:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password_here

# Django
SECRET_KEY=your_django_secret_key_here
JWT_SECRET=your_jwt_secret_here
DEBUG=False
ALLOWED_HOSTS=10.147.19.100,127.0.0.1,localhost

# Deployment
ENVIRONMENT=production
```

## Network Architecture

```
┌─────────────────────────────────────────────────┐
│         INTERNET / EXTERNAL ACCESS              │
├─────────────────────────────────────────────────┤
│                                                 │
│  HTTP (9080) ──┐                               │
│  HTTPS (9443)──┤──→ Nginx Reverse Proxy       │
│                │                               │
├─────────────────────────────────────────────────┤
│      eventticketing-network (Docker)            │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Django Web  │  │  Celery Worker/Beat  │   │
│  │   (8002)     │  │    (Internal)        │   │
│  └──────────────┘  └──────────────────────┘   │
│         │                    │                 │
│         └────────┬───────────┘                 │
│                  │                             │
│         ┌────────┴─────────┐                  │
│         │                  │                  │
│    ┌─────────┐        ┌───────┐              │
│    │PostgreSQL│       │ Redis │              │
│    │ (5436)  │       │(6381) │              │
│    └─────────┘        └───────┘              │
│                                              │
└─────────────────────────────────────────────┘
```

## Deployment Commands

```bash
# Copy production compose file
scp docker-compose.production.yml n0de@10.147.19.100:/home/n0de/eventticketing/

# Create environment file
ssh n0de@10.147.19.100 'cat > /home/n0de/eventticketing/.env.production << EOF
POSTGRES_PASSWORD=your_secure_password_here
SECRET_KEY=your_django_secret_key_here
JWT_SECRET=your_jwt_secret_here
ENVIRONMENT=production
EOF'

# Deploy
ssh n0de@10.147.19.100 'cd /home/n0de/eventticketing && \
  docker-compose -f docker-compose.production.yml up -d'

# Verify
ssh n0de@10.147.19.100 'cd /home/n0de/eventticketing && \
  docker-compose -f docker-compose.production.yml ps'

# Check logs
ssh n0de@10.147.19.100 'cd /home/n0de/eventticketing && \
  docker-compose -f docker-compose.production.yml logs -f web'
```

## Health Checks

All services include health checks that will automatically restart on failure.

Monitor with:
```bash
ssh n0de@10.147.19.100 'docker ps --format "{{.Names}}\t{{.Status}}"'
```

## Backup & Disaster Recovery

PostgreSQL data backed up to: `/home/n0de/eventticketing/backups/`

Restore from backup:
```bash
docker-compose -f docker-compose.production.yml exec postgres \
  psql -U ticketing_user -d eventticketing_prod < backups/latest.sql
```

## Monitoring & Logs

```bash
# All container logs
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f web

# Database logs
docker-compose -f docker-compose.production.yml logs -f postgres

# Nginx logs
docker-compose -f docker-compose.production.yml logs -f nginx
```

---

**Status: ✅ CONFLICT-FREE | READY TO DEPLOY**

