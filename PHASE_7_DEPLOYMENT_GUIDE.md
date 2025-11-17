# Phase 7: Deployment & Production Setup - Complete Guide

**Duration**: 2-3 days  
**Environment**: Docker + Nginx + PostgreSQL + Redis  
**Target**: Production-ready deployment  
**Status**: Configuration Ready

---

## 📋 Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│                 Users (Internet)                │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   Nginx (80/443)│
            │  SSL Termination│
            └────────┬────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌──────────┐
    │Backend  │ │Frontend │ │ Static   │
    │:8000    │ │:3000    │ │ Files    │
    └────┬────┘ └────┬────┘ └──────────┘
         │           │
         └───────┬───┘
                 ▼
        ┌────────────────┐
        │ Docker Network │
        │ (eventticketing)
        └────────┬───────┘
                 │
    ┌────────────┼─────────────┐
    ▼            ▼             ▼
┌────────┐  ┌─────────┐  ┌──────────┐
│Django  │  │Database │  │  Cache   │
│Backend │  │Postgres │  │  Redis   │
└────────┘  │  (5432) │  │ (6379)   │
            └─────────┘  └──────────┘
```

---

## 🔧 Part 1: Production Settings Setup

### Files Created:
- `settings_production.py` - Production Django configuration
- `Dockerfile` - Backend container image
- `docker-compose.yml` - Full stack orchestration
- `nginx.conf` - Nginx reverse proxy configuration

### Key Features:

**Security**:
✅ HTTPS/SSL enforcement  
✅ HSTS headers  
✅ XSS protection  
✅ CSRF protection  
✅ Security headers  

**Performance**:
✅ Gzip compression  
✅ Static file caching  
✅ Connection pooling  
✅ Rate limiting  
✅ Load balancing  

**Reliability**:
✅ Health checks  
✅ Automatic restart  
✅ Logging & monitoring  
✅ Error handling  

---

## 🐳 Part 2: Docker Setup

### Backend Dockerfile
```dockerfile
# Multi-stage build (smaller images)
# Stage 1: Build dependencies
# Stage 2: Runtime only

Features:
✓ Security hardening
✓ Non-root user
✓ Health checks
✓ Optimized layers
✓ Production-ready
```

### Docker Compose Services
```
1. PostgreSQL (Database)
   - Persistent volume
   - Health checks
   - SSL ready
   
2. Redis (Cache & Message Broker)
   - Persistent data
   - Password protected
   - Health checks
   
3. Django Backend
   - Auto migrations
   - Gunicorn server
   - 4 worker processes
   
4. Celery Worker
   - Async task processing
   - Email notifications
   - Background jobs
   
5. Nginx
   - Reverse proxy
   - SSL termination
   - Load balancing
   - Static file serving
   
6. Next.js Frontend
   - Production build
   - API proxy
   - SSR ready
```

---

## 📝 Part 3: Environment Configuration

### Create `.env.production` (DO NOT COMMIT!)

```bash
# Django Settings
DJANGO_SETTINGS_MODULE=eventticketing.settings_production
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=eventticketing
DB_USER=postgres
DB_PASSWORD=secure-password-here
DB_HOST=postgres
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# Email (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=app-specific-password

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# Frontend
NEXT_PUBLIC_API_URL=https://yourdomain.com/api
```

### Generate Secure Values

```bash
# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate strong password
openssl rand -base64 32
```

---

## 🚀 Part 4: Deployment Steps

### Step 1: Prepare Server

```bash
# Update system
apt update && apt upgrade -y

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo apt install docker-compose -y

# Create application directory
mkdir -p /app/eventticketing
cd /app/eventticketing

# Clone repository
git clone <your-repo> .
```

### Step 2: SSL Certificate Setup

```bash
# Option A: Let's Encrypt (Recommended)
sudo apt install certbot python3-certbot-nginx -y
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./ssl/key.pem
sudo chown -R $(whoami): ./ssl

# Option B: Self-signed (Development only)
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
```

### Step 3: Configure Environment

```bash
# Copy environment file
cp .env.production.example .env.production

# Edit with your values
nano .env.production

# Load environment
source .env.production
```

### Step 4: Create Database Init Script

**init.sql**:
```sql
-- Create databases
CREATE DATABASE eventticketing;
CREATE DATABASE eventticketing_test;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set permissions
GRANT ALL PRIVILEGES ON DATABASE eventticketing TO postgres;
GRANT ALL PRIVILEGES ON DATABASE eventticketing_test TO postgres;
```

### Step 5: Build and Start Containers

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Verify status
docker-compose ps

# Check logs
docker-compose logs -f backend
```

### Step 6: Initialize Database

```bash
# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Collect static files
docker-compose exec backend python manage.py collectstatic --noinput

# Create cache table
docker-compose exec backend python manage.py createcachetable
```

### Step 7: Verify Deployment

```bash
# Check health
curl http://localhost/health

# Check API
curl http://localhost/api/v1/health/

# Check admin
curl http://localhost/admin/

# Check frontend
curl http://localhost/
```

---

## 🍐 Part 5: Raspberry Pi Deployment

### Prerequisites

```bash
# Raspberry Pi OS (64-bit recommended)
# - Raspberry Pi 4 (4GB+ RAM minimum)
# - 32GB+ microSD card
# - Good power supply (5V 3A+)
```

### Installation on Raspberry Pi

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y \
    python3-pip \
    python3-venv \
    git \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    certbot

# 3. Install Docker (ARM support)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 4. Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# 5. Install Docker Compose
sudo pip3 install docker-compose

# 6. Clone repository
git clone <your-repo> /home/pi/eventticketing
cd /home/pi/eventticketing

# 7. Configure environment
cp .env.production.example .env.production
nano .env.production

# 8. Reduce resource usage for Pi
# Edit docker-compose.yml:
#   - backend: workers=2 (instead of 4)
#   - Add memory limits to services
#   - Use lighter base images

# 9. Start services
docker-compose up -d

# 10. Monitor resource usage
docker stats
```

### Performance Optimization for Raspberry Pi

```yaml
# docker-compose.yml modifications
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
    
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

postgres:
  environment:
    POSTGRES_MAX_CONNECTIONS: 100
    SHARED_BUFFERS: 256MB
    EFFECTIVE_CACHE_SIZE: 1GB
```

---

## 🛡️ Part 6: Security Hardening

### Firewall Configuration

```bash
# Install UFW
sudo apt install ufw

# Configure rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Verify
sudo ufw status
```

### SSH Security

```bash
# Edit /etc/ssh/sshd_config
# - Disable root login: PermitRootLogin no
# - Disable password auth: PasswordAuthentication no
# - Use key-based auth only

# Restart SSH
sudo systemctl restart sshd
```

### Regular Updates

```bash
# Enable automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 📊 Part 7: Monitoring & Maintenance

### Logging

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f nginx
docker-compose logs -f postgres

# Log rotation
docker-compose exec backend tail -f /app/logs/django.log
```

### Backups

```bash
# Database backup
docker-compose exec postgres pg_dump -U postgres eventticketing > backup.sql

# Restore from backup
docker-compose exec postgres psql -U postgres < backup.sql

# Auto-backup script
#!/bin/bash
BACKUP_DIR="/backups/eventticketing"
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec postgres pg_dump -U postgres eventticketing > "$BACKUP_DIR/backup_$DATE.sql"
```

### Health Monitoring

```bash
# Docker health status
docker ps --format "table {{.Names}}\t{{.Status}}"

# Container resource usage
docker stats

# Service status
docker-compose ps
```

### SSL Certificate Renewal

```bash
# Automatic renewal (cron job)
0 12 * * * certbot renew --quiet && cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /app/eventticketing/ssl/cert.pem
```

---

## 🚨 Part 8: Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Container won't start | `docker-compose logs <service>` |
| Database connection failed | Check `DB_HOST`, `DB_PASSWORD` in `.env` |
| Static files not loading | Run `collectstatic --noinput` |
| Nginx 502 error | Check backend health, check logs |
| High memory usage | Reduce worker count, increase swap |
| Slow queries | Enable database query logging, add indexes |

### Emergency Recovery

```bash
# Stop all containers
docker-compose down

# Remove containers
docker-compose rm -f

# Clean volumes (WARNING: loses data!)
docker volume prune

# Restart fresh
docker-compose up -d
```

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] All code committed and tested
- [ ] Environment file configured
- [ ] SSL certificates ready
- [ ] Database backups created
- [ ] Firewall configured
- [ ] DNS records updated

### Deployment
- [ ] Docker images built
- [ ] Containers started
- [ ] Database migrated
- [ ] Admin user created
- [ ] Static files collected
- [ ] Health checks passing

### Post-Deployment
- [ ] All endpoints working
- [ ] Frontend loads correctly
- [ ] Admin panel accessible
- [ ] Email sending working
- [ ] Logging configured
- [ ] Monitoring setup
- [ ] Backup schedule active

---

## 🎯 Success Metrics

After deployment, verify:

✅ Backend API responding (< 200ms)  
✅ Frontend loading (< 1s)  
✅ Database queries fast (< 50ms)  
✅ SSL certificate valid  
✅ All endpoints working  
✅ Admin panel secure  
✅ Email sending  
✅ Background jobs running  

---

## 📞 Support & Rollback

### If Something Goes Wrong

```bash
# 1. Check logs
docker-compose logs -f

# 2. Restart service
docker-compose restart backend

# 3. Rebuild if needed
docker-compose down
docker-compose build
docker-compose up -d

# 4. Restore from backup
docker-compose exec postgres psql -U postgres < backup.sql
```

---

## 📈 Next Steps

After successful deployment:
- Monitor performance metrics
- Set up automated backups
- Configure CDN for static files
- Scale horizontally if needed
- Plan capacity expansion

---

**Phase 7 Deployment Guide Complete!**

Ready for Phase 8: Testing & Cleanup

