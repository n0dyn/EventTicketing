# Docker Deployment Guide

**EventTicketing Platform - Production Docker Deployment**

This guide covers deploying the EventTicketing platform using Docker and Docker Compose for production environments.

---

## 🎯 Overview

### Architecture Components
- **Frontend**: Next.js 13+ application with PWA capabilities
- **Backend**: FastAPI with async PostgreSQL and Redis
- **Database**: PostgreSQL 15+ with extensions
- **Cache**: Redis 7+ for sessions and caching
- **Reverse Proxy**: Nginx for load balancing and SSL termination
- **Monitoring**: Optional Prometheus and Grafana stack

### System Requirements
- **CPU**: 2+ cores (4+ recommended for production)
- **Memory**: 4GB RAM minimum (8GB+ recommended)
- **Storage**: 20GB minimum (SSD recommended)
- **OS**: Linux (Ubuntu 20.04+ or CentOS 8+)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

---

## 📋 Pre-Deployment Checklist

### 1. Server Preparation
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker-compose --version
```

### 2. Environment Setup
```bash
# Create project directory
sudo mkdir -p /opt/eventticket
sudo chown $USER:$USER /opt/eventticket
cd /opt/eventticket

# Clone repository
git clone https://github.com/your-org/eventticket.git .

# Create environment files
cp .env.example .env.production
```

### 3. SSL Certificates
```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# Generate certificates (replace with your domain)
sudo certbot certonly --standalone -d api.yourdomain.com -d app.yourdomain.com

# Verify certificates
sudo ls -la /etc/letsencrypt/live/yourdomain.com/
```

---

## 🔧 Configuration

### 1. Production Environment Variables
Create `/opt/eventticket/.env.production`:

```bash
# Application Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secure-secret-key-here
API_V1_STR=/api/v1

# Database Configuration
DATABASE_URL=postgresql://eventticket@postgres:5432/eventticket_prod
POSTGRES_USER=eventticket
POSTGRES_PASSWORD=secure_database_password
POSTGRES_DB=eventticket_prod

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Security Settings
BACKEND_CORS_ORIGINS=["https://app.yourdomain.com","https://admin.yourdomain.com"]
ALLOWED_HOSTS=["api.yourdomain.com","yourdomain.com"]

# Email Settings (SendGrid example)
SMTP_TLS=true
SMTP_PORT=587
SMTP_HOST=smtp.sendgrid.net
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAILS_FROM_EMAIL=noreply@yourdomain.com
EMAILS_FROM_NAME="EventTicketing Platform"

# File Storage (AWS S3 example)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=eventticket-uploads
AWS_REGION=us-west-2

# Payment Processing (Stripe)
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Monitoring and Logging
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
LOG_LEVEL=INFO

# Frontend Settings
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
NEXT_PUBLIC_GOOGLE_ANALYTICS_ID=GA-MEASUREMENT-ID
```

### 2. Production Docker Compose
Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    networks:
      - eventticket_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis Cache
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-}
    volumes:
      - redis_data:/data
    networks:
      - eventticket_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    env_file:
      - .env.production
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    networks:
      - eventticket_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Frontend Application
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
        - NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}
    restart: unless-stopped
    env_file:
      - .env.production
    depends_on:
      - backend
    networks:
      - eventticket_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/sites-enabled:/etc/nginx/sites-enabled:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - backend
      - frontend
    networks:
      - eventticket_network
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  eventticket_network:
    driver: bridge
```

### 3. Nginx Configuration
Create `nginx/nginx.conf`:

```nginx
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/javascript application/xml+rss 
               application/json application/xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=app:10m rate=5r/s;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # Load site configurations
    include /etc/nginx/sites-enabled/*;
}
```

Create `nginx/sites-enabled/eventticket.conf`:

```nginx
# Frontend Application
server {
    listen 80;
    listen [::]:80;
    server_name app.yourdomain.com yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name app.yourdomain.com yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        limit_req zone=app burst=20 nodelay;
    }
}

# Backend API
server {
    listen 80;
    listen [::]:80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        limit_req zone=api burst=50 nodelay;
    }

    # WebSocket support
    location /api/v1/ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

---

## 🚀 Deployment Process

### 1. Build and Deploy
```bash
# Navigate to project directory
cd /opt/eventticket

# Pull latest code
git pull origin main

# Build and start services
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

### 2. Database Migration
```bash
# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Create initial admin user (optional)
docker-compose -f docker-compose.prod.yml exec backend python scripts/create_admin.py
```

### 3. Health Check
```bash
# Check all services
curl -f https://api.yourdomain.com/health
curl -f https://app.yourdomain.com

# Check database connection
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.db.session import SessionLocal
db = SessionLocal()
print('Database connection: OK')
db.close()
"

# Check Redis connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

---

## 📊 Monitoring and Maintenance

### 1. Log Management
```bash
# View service logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f nginx

# Log rotation setup
sudo nano /etc/logrotate.d/eventticket
```

Add to `/etc/logrotate.d/eventticket`:
```
/opt/eventticket/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
```

### 2. Backup Strategy
```bash
# Database backup script
#!/bin/bash
BACKUP_DIR="/opt/eventticket/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Database backup
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump \
  -U $POSTGRES_USER $POSTGRES_DB | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Remove backups older than 30 days
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: db_backup_$DATE.sql.gz"
```

### 3. SSL Certificate Renewal
```bash
# Auto-renewal with cron
sudo crontab -e

# Add this line for automatic renewal
0 0,12 * * * /usr/bin/certbot renew --quiet --reload-services nginx
```

---

## 🔧 Scaling and Performance

### 1. Horizontal Scaling
```yaml
# In docker-compose.prod.yml, increase replicas:
services:
  backend:
    deploy:
      replicas: 4  # Scale backend
  
  frontend:
    deploy:
      replicas: 3  # Scale frontend
```

### 2. Load Balancing
Update Nginx configuration for multiple backend instances:
```nginx
upstream backend_pool {
    least_conn;
    server backend_1:8000 max_fails=3 fail_timeout=30s;
    server backend_2:8000 max_fails=3 fail_timeout=30s;
    server backend_3:8000 max_fails=3 fail_timeout=30s;
    server backend_4:8000 max_fails=3 fail_timeout=30s;
}

server {
    # ... SSL config ...
    
    location / {
        proxy_pass http://backend_pool;
        # ... other proxy settings ...
    }
}
```

### 3. Performance Tuning
```bash
# Optimize Docker settings
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Optimize PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres bash -c "
echo 'shared_preload_libraries = \"pg_stat_statements\"' >> /var/lib/postgresql/data/postgresql.conf
echo 'max_connections = 200' >> /var/lib/postgresql/data/postgresql.conf
echo 'shared_buffers = 256MB' >> /var/lib/postgresql/data/postgresql.conf
"

# Restart services
docker-compose -f docker-compose.prod.yml restart postgres backend
```

---

## 🚨 Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs service_name

# Check resource usage
docker stats

# Restart specific service
docker-compose -f docker-compose.prod.yml restart service_name
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL logs
docker-compose -f docker-compose.prod.yml logs postgres

# Test connection
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"

# Reset database connection
docker-compose -f docker-compose.prod.yml restart postgres backend
```

#### 3. SSL Certificate Issues
```bash
# Check certificate validity
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/cert.pem -text -noout

# Renew certificate manually
sudo certbot renew --force-renewal

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

#### 4. High Memory Usage
```bash
# Check memory usage per container
docker stats --no-stream

# Increase swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📋 Production Checklist

### Pre-Launch
- [ ] SSL certificates installed and verified
- [ ] Environment variables configured
- [ ] Database migrations completed
- [ ] Email service configured and tested
- [ ] Payment processing configured
- [ ] File storage configured
- [ ] Monitoring and logging setup
- [ ] Backup strategy implemented
- [ ] Load testing completed
- [ ] Security audit performed

### Post-Launch
- [ ] Monitor service health
- [ ] Verify SSL certificate auto-renewal
- [ ] Test backup and restore procedures
- [ ] Set up alerting for critical issues
- [ ] Document incident response procedures
- [ ] Schedule regular security updates

---

**Deployment completed! Your EventTicketing platform is now running in production.**

For additional support and advanced configurations, refer to the [Operations Manual](./operations-manual.md) and [Security Guide](./security-guide.md).