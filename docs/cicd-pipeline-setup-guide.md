# CI/CD Pipeline Setup Guide

## EventTicketing Platform - Complete CI/CD Implementation

This guide provides comprehensive instructions for setting up and managing the CI/CD pipeline for the EventTicketing platform.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Pipeline Configuration](#pipeline-configuration)
5. [Security Setup](#security-setup)
6. [Environment Configuration](#environment-configuration)
7. [Testing Configuration](#testing-configuration)
8. [Deployment Setup](#deployment-setup)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The CI/CD pipeline provides:

- **Automated Testing**: Unit, integration, and E2E tests with coverage reporting
- **Code Quality**: Linting, formatting, type checking, and security scanning
- **Security**: Vulnerability scanning, dependency auditing, and secret management
- **Deployment**: Multi-environment deployments with rollback capabilities
- **Monitoring**: Health checks, performance metrics, and alerting
- **Automation**: Dependency updates, release management, and notifications

### Pipeline Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Development   │ →  │     Staging     │ →  │   Production    │
│                 │    │                 │    │                 │
│ • Local Testing │    │ • Auto Deploy  │    │ • Manual Deploy│
│ • Code Quality  │    │ • Integration   │    │ • Blue-Green   │
│ • Unit Tests    │    │ • E2E Tests     │    │ • Health Checks │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🔧 Prerequisites

### Required Tools & Services

1. **GitHub Repository** with admin access
2. **Docker Hub Account** (or alternative container registry)
3. **Cloud Provider Account** (AWS, GCP, or Azure for deployment)
4. **Domain Name** for staging/production environments
5. **Stripe Account** for payment processing

### Local Development Requirements

```bash
# Backend
- Python 3.11+
- Poetry 1.7.1+
- PostgreSQL 15+
- Redis 7+

# Frontend
- Node.js 18+
- npm 8+

# Docker
- Docker Engine 20.10+
- Docker Compose 2.0+
```

---

## 🚀 Initial Setup

### Step 1: Clone and Prepare Repository

```bash
# Clone the repository
git clone https://github.com/your-username/EventTicketing.git
cd EventTicketing

# Create development branch
git checkout -b develop
git push -u origin develop

# Verify CI/CD files exist
ls -la .github/workflows/
```

### Step 2: Repository Settings Configuration

#### Branch Protection Rules

Configure protection for `main` and `develop` branches:

**For `main` branch:**
```yaml
Protection Rules:
- Require pull request reviews: 2 reviewers
- Dismiss stale reviews: ✓
- Require review from code owners: ✓
- Restrict pushes: ✓
- Require status checks: ✓
- Require branches to be up to date: ✓
- Require linear history: ✓

Required Status Checks:
- Backend CI/CD / lint-and-format
- Backend CI/CD / test
- Frontend CI/CD / lint-and-format  
- Frontend CI/CD / test
- Frontend CI/CD / build
- Full Stack CI/CD / integration-tests
```

**For `develop` branch:**
```yaml
Protection Rules:
- Require pull request reviews: 1 reviewer
- Dismiss stale reviews: ✓
- Require status checks: ✓
- Require branches to be up to date: ✓

Required Status Checks:
- Same as main branch
```

#### Environments Setup

Create environments in GitHub repository settings:

**Staging Environment:**
```yaml
Environment Name: staging
Protection Rules:
- Required reviewers: 1
- Wait timer: 0 minutes
- Deployment branches: develop only

Environment Variables:
- NEXT_PUBLIC_API_URL: https://staging-api.eventtickets.example.com/api/v1
- NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: pk_test_...
```

**Production Environment:**
```yaml
Environment Name: production
Protection Rules:
- Required reviewers: 2
- Wait timer: 5 minutes
- Deployment branches: main only

Environment Variables:
- NEXT_PUBLIC_API_URL: https://api.eventtickets.example.com/api/v1
- NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: pk_live_...
```

---

## 🔒 Security Setup

### GitHub Secrets Configuration

Add these secrets in GitHub repository settings → Secrets and variables → Actions:

#### Required Secrets

```bash
# Docker Registry
DOCKER_USERNAME=your_dockerhub_username
DOCKER_PASSWORD=your_dockerhub_token

# Stripe Keys
STRIPE_SECRET_KEY=sk_live_...  # Production
STRIPE_PUBLISHABLE_KEY=pk_live_...  # Production
STRIPE_SECRET_KEY_TEST=sk_test_...  # Testing
STRIPE_PUBLISHABLE_KEY_TEST=pk_test_...  # Testing

# Database (Production)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@yourdomain.com
SMTP_PASSWORD=your_app_password
EMAILS_FROM_EMAIL=notifications@yourdomain.com
EMAILS_FROM_NAME=EventTicketing

# Application Security
SECRET_KEY=your_super_secret_jwt_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional: Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

#### Secret Generation Commands

```bash
# Generate JWT secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate Docker Hub token
# Go to Docker Hub → Account Settings → Security → New Access Token
```

### Security Best Practices

1. **Secret Rotation**: Rotate secrets every 90 days
2. **Least Privilege**: Use minimal required permissions
3. **Environment Separation**: Different secrets for staging/production
4. **Audit Logs**: Monitor secret usage and access
5. **Dependency Scanning**: Enable Dependabot alerts

---

## 🌍 Environment Configuration

### Development Environment

Create `.env.local` files (not committed to git):

**Backend (`backend/.env.local`):**
```env
DATABASE_URL=postgresql+asyncpg://user@localhost:5432/eventtickets_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev_secret_key_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
PROJECT_NAME=EventTicketing Dev
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
SMTP_HOST=localhost
SMTP_PORT=1025  # Use MailHog for dev
FRONTEND_URL=http://localhost:3000
```

**Frontend (`frontend/.env.local`):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_APP_NAME=EventTicketing Dev
```

### Docker Development Setup

```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop environment
docker-compose down
```

---

## 🧪 Testing Configuration

### Backend Testing Setup

The pipeline includes comprehensive backend testing:

```bash
# Test configuration in backend/pytest.ini
# Coverage settings in backend/pyproject.toml

# Run tests locally
cd backend
poetry install
poetry run pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Frontend Testing Setup

```bash
# Test configuration in frontend/jest.config.js
# E2E configuration in frontend/playwright.config.ts

# Run unit tests
cd frontend
npm install
npm run test:coverage

# Run E2E tests
npm run e2e

# Run with UI (for debugging)
npm run e2e:ui
```

### Performance Testing Setup

```bash
# Lighthouse configuration in frontend/lighthouserc.json
# Run performance audit
cd frontend
npm run lighthouse

# View Lighthouse report
open ./lighthouse-ci-results/
```

---

## 🚀 Deployment Setup

### Infrastructure Requirements

#### Staging Environment
- **Domain**: `staging.eventtickets.example.com`
- **API Domain**: `staging-api.eventtickets.example.com`
- **Database**: PostgreSQL (separate from production)
- **Cache**: Redis instance
- **Storage**: S3-compatible storage for uploads
- **SSL**: Let's Encrypt or cloud provider SSL

#### Production Environment
- **Domain**: `eventtickets.example.com`
- **API Domain**: `api.eventtickets.example.com`
- **Database**: PostgreSQL with backups
- **Cache**: Redis with persistence
- **Storage**: S3-compatible with CDN
- **SSL**: Premium SSL certificate
- **Monitoring**: APM and logging services

### Deployment Methods

#### Method 1: Docker-based Deployment

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  backend:
    image: yourusername/eventtickets-backend:latest
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  frontend:
    image: yourusername/eventtickets-frontend:latest
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
    ports:
      - "3000:3000"
    depends_on:
      - backend

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### Method 2: Kubernetes Deployment

```yaml
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eventtickets-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: eventtickets-backend
  template:
    metadata:
      labels:
        app: eventtickets-backend
    spec:
      containers:
      - name: backend
        image: yourusername/eventtickets-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: eventtickets-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: eventtickets-secrets
              key: redis-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Database Migration Strategy

```bash
# Production migration checklist
1. Create database backup
2. Test migration on staging
3. Schedule maintenance window
4. Apply migration with rollback plan
5. Verify application functionality
6. Monitor performance metrics

# Migration commands
cd backend
poetry run alembic upgrade head

# Rollback if needed
poetry run alembic downgrade -1
```

---

## 📊 Monitoring & Maintenance

### Health Monitoring

The pipeline includes comprehensive health checks:

```bash
# Health check endpoints
GET /health              # Application health
GET /health/database     # Database connectivity
GET /health/redis        # Redis connectivity
GET /health/detailed     # Comprehensive health info
```

### Performance Monitoring

```javascript
// Frontend performance monitoring
// Implemented in src/lib/monitoring.js

// Core Web Vitals tracking
// Lighthouse CI integration
// Bundle size monitoring
// Runtime performance metrics
```

### Alerting Setup

Configure alerts for:

- **Application Errors**: 5xx responses > 5%
- **Performance**: Response time > 2s
- **Availability**: Uptime < 99.9%
- **Security**: Vulnerability detection
- **Dependencies**: Outdated packages

### Maintenance Tasks

#### Weekly Tasks
- Review dependency update PRs
- Check security vulnerability reports
- Review CI/CD pipeline metrics
- Update staging environment data

#### Monthly Tasks
- Rotate secrets and keys
- Review and update monitoring thresholds
- Performance optimization review
- Security audit review

#### Quarterly Tasks
- Infrastructure cost optimization
- CI/CD pipeline performance review
- Disaster recovery testing
- Team training and documentation updates

---

## 🔧 Troubleshooting

### Common Issues & Solutions

#### CI/CD Pipeline Failures

**Issue**: Tests failing due to database connection
```bash
# Solution: Check database service health
# Review service configuration in workflow
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
      POSTGRES_DB: test_eventtickets
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

**Issue**: Docker build failures
```bash
# Solution: Check Dockerfile and dependencies
# Review build logs for specific errors
# Verify base image compatibility
# Check dependency versions
```

**Issue**: E2E test failures
```bash
# Solution: Check test environment setup
# Verify application startup timing
# Review Playwright configuration
# Check test data setup
```

#### Deployment Issues

**Issue**: Environment variables not set
```bash
# Solution: Verify GitHub secrets configuration
# Check environment-specific variables
# Validate secret names match workflow
```

**Issue**: Database migration failures
```bash
# Solution: Check migration syntax
# Verify database permissions
# Test migration on staging first
# Prepare rollback plan
```

**Issue**: SSL certificate problems
```bash
# Solution: Verify domain configuration
# Check DNS settings
# Renew certificates if expired
# Update load balancer settings
```

### Debug Commands

```bash
# Check workflow status
gh workflow list
gh run list --workflow=backend-ci.yml

# View workflow logs
gh run view <run-id> --log

# Test Docker builds locally
docker build -f backend/Dockerfile.prod ./backend
docker build -f frontend/Dockerfile.prod ./frontend

# Test database connection
cd backend
poetry run python -c "
from app.db.session import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection successful')
"

# Test frontend build
cd frontend
npm run build
npm run start
```

### Performance Optimization

```bash
# Backend optimization
- Database query optimization
- Redis caching implementation
- API response compression
- Background task optimization

# Frontend optimization
- Code splitting implementation
- Image optimization
- Bundle size reduction
- CDN configuration

# CI/CD optimization
- Build caching
- Parallel job execution
- Dependency caching
- Test optimization
```

---

## 📚 Additional Resources

### Documentation Links
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Playwright Testing](https://playwright.dev/docs/intro)
- [Jest Testing Framework](https://jestjs.io/docs/getting-started)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Next.js Deployment](https://nextjs.org/docs/deployment)

### Monitoring Tools
- **Application Performance**: New Relic, Datadog, Sentry
- **Infrastructure**: Prometheus, Grafana, AWS CloudWatch
- **Log Management**: ELK Stack, Splunk, Fluentd
- **Security**: Snyk, OWASP ZAP, SonarQube

### Community Resources
- [FastAPI Community](https://fastapi.tiangolo.com/help-fastapi/)
- [Next.js Community](https://nextjs.org/community)
- [GitHub Actions Community](https://github.com/actions/community)
- [Docker Community](https://www.docker.com/community)

---

## ✅ Setup Completion Checklist

Use this checklist to verify your CI/CD pipeline setup:

### Repository Setup
- [ ] Repository created with proper branch structure
- [ ] Branch protection rules configured
- [ ] Environments created (staging, production)
- [ ] Team access permissions set

### Security Configuration
- [ ] All required secrets configured
- [ ] Environment variables set
- [ ] Dependency scanning enabled
- [ ] Code scanning enabled

### Pipeline Configuration
- [ ] All workflow files present and validated
- [ ] Test configurations working
- [ ] Docker builds successful
- [ ] Deployment targets configured

### Testing Setup
- [ ] Backend tests passing locally
- [ ] Frontend tests passing locally
- [ ] E2E tests configured and working
- [ ] Performance audits running

### Deployment Setup
- [ ] Infrastructure provisioned
- [ ] Domain names configured
- [ ] SSL certificates installed
- [ ] Database migrations working
- [ ] Health checks responding

### Monitoring Setup
- [ ] Application monitoring configured
- [ ] Alert rules defined
- [ ] Log aggregation working
- [ ] Performance metrics collecting

### Documentation
- [ ] Team training completed
- [ ] Runbooks created
- [ ] Troubleshooting guides available
- [ ] Maintenance procedures documented

---

*Last Updated: August 2025*
*Version: 1.0.0*

For questions or issues, create a GitHub issue or contact the development team.