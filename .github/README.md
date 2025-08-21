# CI/CD Pipeline Documentation

This directory contains the comprehensive CI/CD pipeline configuration for the EventTicketing platform, implementing automated testing, security scanning, and deployment workflows.

## 🚀 Workflow Overview

### Core Workflows

#### 1. **Backend CI/CD** (`backend-ci.yml`)
- **Triggers**: Push/PR to `main`/`develop` with backend changes
- **Jobs**:
  - **Lint & Format**: Black, isort, Ruff, MyPy
  - **Testing**: pytest with PostgreSQL/Redis services
  - **Security Scan**: Safety, Bandit vulnerability scanning
  - **Build & Push**: Docker image building and registry push
  - **Deploy**: Staging (develop) and Production (main) deployment

#### 2. **Frontend CI/CD** (`frontend-ci.yml`)
- **Triggers**: Push/PR to `main`/`develop` with frontend changes
- **Jobs**:
  - **Lint & Format**: ESLint, TypeScript checking, Prettier
  - **Testing**: Jest unit tests with coverage
  - **Build**: Next.js production build
  - **Security Scan**: npm audit, dependency vulnerability check
  - **E2E Testing**: Playwright cross-browser testing
  - **Performance**: Lighthouse audit on PRs
  - **Deploy**: Staging and Production deployment

#### 3. **Full Stack CI/CD** (`full-stack-ci.yml`)
- **Triggers**: Push/PR to `main`/`develop`, manual dispatch
- **Features**:
  - **Change Detection**: Only runs jobs for modified services
  - **Parallel Execution**: Backend and frontend jobs run concurrently
  - **Integration Testing**: Full stack testing with real services
  - **Security Audit**: Trivy filesystem scanning
  - **Deployment**: Coordinated full-stack deployment
  - **Rollback**: Automatic rollback on deployment failure

#### 4. **Dependency Updates** (`dependency-updates.yml`)
- **Triggers**: Weekly schedule (Mondays 8 AM UTC), manual dispatch
- **Features**:
  - **Automated Updates**: Poetry (backend) and npm (frontend)
  - **Testing**: Runs full test suite after updates
  - **PR Creation**: Automatic pull requests for dependency updates
  - **Security Monitoring**: Creates issues for security vulnerabilities

#### 5. **Release Management** (`release.yml`)
- **Triggers**: Version tags (`v*.*.*`), manual dispatch
- **Features**:
  - **Version Validation**: Semantic versioning compliance
  - **Changelog Generation**: Automatic changelog from git history
  - **Release Notes**: Comprehensive release documentation
  - **Docker Builds**: Multi-arch production image builds
  - **Production Deployment**: Automated production deployment for stable releases

### 🛡️ Security Features

#### Vulnerability Scanning
- **Backend**: Safety (Python dependencies), Bandit (code analysis)
- **Frontend**: npm audit (Node dependencies)
- **Infrastructure**: Trivy (filesystem, container images)

#### Code Quality
- **Backend**: Black formatting, isort imports, Ruff linting, MyPy typing
- **Frontend**: ESLint rules, Prettier formatting, TypeScript strict mode

#### Secret Management
- Environment-specific secrets stored in GitHub Secrets
- No hardcoded credentials in codebase
- Secure container image builds

### 📊 Testing Strategy

#### Backend Testing
- **Unit Tests**: pytest with async support
- **Integration Tests**: Real PostgreSQL/Redis services
- **Coverage**: Minimum 70% threshold
- **Performance**: Database query optimization

#### Frontend Testing
- **Unit Tests**: Jest with React Testing Library
- **Component Tests**: Isolated component testing
- **E2E Tests**: Playwright cross-browser testing
- **Performance**: Lighthouse audit thresholds

#### Full Stack Testing
- **Integration**: End-to-end API and UI testing
- **Smoke Tests**: Post-deployment health checks
- **Load Testing**: Performance under load (future enhancement)

### 🚀 Deployment Pipeline

#### Environments
1. **Development**: Local development with Docker Compose
2. **Staging**: `develop` branch auto-deployment
3. **Production**: `main` branch with manual approval

#### Deployment Features
- **Blue-Green Deployment**: Zero-downtime deployments
- **Health Checks**: Automated post-deployment verification
- **Rollback**: Automatic rollback on failure detection
- **Database Migrations**: Safe migration with backup/rollback
- **Monitoring**: Real-time deployment monitoring

### 📋 Configuration Files

#### Docker Configuration
- `backend/Dockerfile.prod`: Production backend container
- `frontend/Dockerfile.prod`: Production frontend container
- `docker-compose.yml`: Development environment

#### Testing Configuration
- `backend/pytest.ini`: Backend test configuration
- `frontend/jest.config.js`: Frontend test configuration  
- `frontend/playwright.config.ts`: E2E test configuration
- `frontend/lighthouserc.json`: Performance audit configuration

#### Code Quality
- `backend/pyproject.toml`: Python dependencies and tools
- `frontend/.prettierrc`: Code formatting rules
- `frontend/.eslintrc.json`: Linting rules

### 🔧 Setup Instructions

#### Required Secrets
Configure these secrets in GitHub repository settings:

```
DOCKER_USERNAME          # Docker Hub username
DOCKER_PASSWORD          # Docker Hub password/token
STRIPE_SECRET_KEY         # Stripe secret key for production
STRIPE_PUBLISHABLE_KEY    # Stripe publishable key for production
SLACK_WEBHOOK_URL         # Slack notifications (optional)
```

#### Environment Variables
Each environment should have:
- Database connection strings
- Redis connection URLs
- API keys and secrets
- Frontend configuration

#### Branch Protection Rules
Recommended settings for main/develop branches:
- Require pull request reviews (2 for main, 1 for develop)
- Require status checks to pass
- Require branches to be up to date
- Restrict pushes to matching branches
- Require linear history

### 📈 Monitoring & Alerts

#### Health Monitoring
- Application health endpoints (`/health`)
- Database connectivity checks
- Redis cache availability
- Performance metrics collection

#### Error Tracking
- Centralized error logging
- Exception monitoring
- Performance degradation alerts
- Security incident notifications

#### Deployment Monitoring
- Deployment success/failure notifications
- Performance impact monitoring
- Rollback trigger conditions
- SLA compliance tracking

### 🚀 Advanced Features

#### Performance Optimization
- Build caching for faster CI runs
- Parallel job execution
- Dependency caching
- Docker layer caching

#### Scalability
- Matrix builds for multiple environments
- Parallel testing across services
- Horizontal scaling support
- Load balancer integration

#### Observability
- Comprehensive logging
- Metrics collection
- Distributed tracing support
- Performance profiling

### 📚 Best Practices

#### Commit Convention
Use conventional commits for automatic changelog generation:
- `feat:` New features
- `fix:` Bug fixes
- `chore:` Maintenance tasks
- `docs:` Documentation updates
- `refactor:` Code refactoring
- `test:` Test additions/updates

#### PR Guidelines
- Keep PRs focused and small
- Include comprehensive test coverage
- Update documentation as needed
- Follow code review checklist
- Ensure CI passes before merge

#### Security Guidelines
- Regular dependency updates
- Vulnerability scanning
- Secret rotation
- Access control review
- Security incident response

### 🔄 Maintenance

#### Regular Tasks
- Weekly dependency updates review
- Monthly security audit review
- Quarterly CI/CD pipeline review
- Continuous monitoring optimization

#### Troubleshooting
- Check workflow logs for failures
- Review deployment status dashboards
- Monitor application health endpoints
- Verify environment configurations

---

For more information, refer to the individual workflow files and the main project documentation.