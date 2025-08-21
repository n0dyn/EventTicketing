# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Docker Environment (Recommended)
```bash
# Start all services in development mode
docker-compose up -d

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down
```

### Backend Development
```bash
cd backend

# Install dependencies with Poetry
poetry install

# Run backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic upgrade head  # Apply migrations
alembic revision --autogenerate -m "description"  # Create new migration

# Code quality
black .  # Format code
isort .  # Sort imports
ruff check .  # Lint code
mypy .  # Type checking

# Testing
pytest  # Run all tests
pytest --cov  # Run tests with coverage
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Code quality
npm run lint  # ESLint
npm run type-check  # TypeScript checking

# Testing
npm test  # Run Jest tests
npm run test:watch  # Watch mode
```

## Project Architecture

### High-Level Structure
- **Backend**: FastAPI application with SQLAlchemy ORM and PostgreSQL database
- **Frontend**: Next.js 13+ application with TypeScript, Tailwind CSS, and Redux Toolkit
- **Database**: PostgreSQL with Alembic migrations
- **Cache**: Redis for session management and caching
- **Containerization**: Docker with development-focused docker-compose setup

### Backend Architecture (`backend/app/`)
- **API Layer** (`api/v1/endpoints/`): REST endpoints organized by domain (auth, users, events, tickets, orders, payments, attendees, organizations)
- **Models** (`models/`): SQLAlchemy ORM models defining database schema
- **Schemas** (`schemas/`): Pydantic models for request/response validation and serialization
- **Services** (`services/`): Business logic layer, isolated from HTTP and database concerns
- **Core** (`core/`): Configuration, security utilities, and shared application components
- **Database** (`db/`): Database session management and connection setup

### Frontend Architecture (`frontend/src/`)
- **App Router** (`app/`): Next.js 13+ app directory with nested layouts and pages
- **Components** (`components/`): Reusable UI components organized by domain (payment, tickets, ui)
- **API Layer** (`lib/api/`): Axios-based API client services for backend communication
- **State Management** (`store/`, `context/`): Redux Toolkit for global state, React Context for auth
- **Types** (`types/`): TypeScript type definitions matching backend schemas
- **Hooks** (`hooks/`): Custom React hooks including authentication and toast notifications

### Key Domain Models
- **Users**: Authentication and user management with role-based access
- **Organizations**: Multi-tenant event organizing entities
- **Events**: Core event information with categories and metadata
- **Tickets**: Ticket types with price tiers and promotional codes
- **Orders**: Purchase transactions linking users to tickets
- **Payments**: Stripe integration for payment processing
- **Attendees**: Individual ticket holders with check-in capabilities

### API Design Patterns
- **RESTful endpoints** following `/api/v1/{domain}` structure
- **Dependency injection** for database sessions and authentication
- **Pydantic validation** for all request/response data
- **JWT authentication** with OAuth2 password bearer flow
- **Role-based authorization** using FastAPI dependencies

### Database Design
- **PostgreSQL** with async SQLAlchemy 2.0+ 
- **Alembic migrations** for schema versioning
- **Relationship modeling** with proper foreign keys and constraints
- **Indexing strategy** for performance optimization

### Frontend Patterns
- **Server-side rendering** with Next.js App Router
- **Component composition** using Radix UI primitives
- **Form handling** with React Hook Form and Zod validation
- **State normalization** using Redux Toolkit Query
- **Responsive design** with Tailwind CSS utility classes

## Environment Configuration

### Backend Environment Variables
Key variables defined in `backend/app/core/config.py`:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection for caching
- `SECRET_KEY`: JWT signing key
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`: Payment processing
- `SMTP_*`: Email configuration for notifications

### Frontend Environment Variables
- `NEXT_PUBLIC_API_URL`: Backend API base URL
- Stripe public keys for payment forms

## Testing Strategy

### Backend Testing
- **pytest** with async support for database testing
- **Test database** isolation using transactions
- **Fixture-based** setup for consistent test data
- **Coverage reporting** to ensure adequate test coverage

### Frontend Testing
- **Jest** with React Testing Library for component testing
- **TypeScript** integration for type-safe tests
- **Mock API responses** for isolated component testing

## Development Workflow

### Code Quality Standards
- **Backend**: Black formatting, isort import sorting, ruff linting, mypy type checking
- **Frontend**: ESLint with Next.js config, TypeScript strict mode, Prettier formatting
- **Commit conventions**: Use descriptive commit messages focusing on the "why"

### Database Changes
1. Modify SQLAlchemy models in `backend/app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review and edit generated migration if needed
4. Apply migration: `alembic upgrade head`
5. Update corresponding Pydantic schemas in `backend/app/schemas/`

### API Development
1. Define endpoint in appropriate `backend/app/api/v1/endpoints/` file
2. Implement business logic in corresponding `backend/app/services/` file
3. Create/update Pydantic schemas for request/response validation
4. Add frontend API client methods in `frontend/src/lib/api/`
5. Update TypeScript types in `frontend/src/types/`

### Component Development
1. Follow existing patterns in `frontend/src/components/`
2. Use Radix UI primitives from `frontend/src/components/ui/`
3. Implement responsive design with Tailwind CSS
4. Add TypeScript interfaces for component props
5. Include accessibility considerations (ARIA labels, keyboard navigation)

## Memories

### Development Interactions
- sounds goood did we save that to our memory?