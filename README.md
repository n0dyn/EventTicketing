# EventTicketing

A modern, open-source event ticketing and management platform built with Python (FastAPI) and Next.js.

## Features

- 🎫 Sell tickets to events with customizable ticket types
- 📱 Mobile-friendly responsive design
- 📊 Real-time event statistics and reporting
- 💲 Multiple payment gateway integrations (Stripe, PayPal)
- 🧩 Customizable event pages and tickets
- 👥 Comprehensive attendee management
- 📱 QR code check-in system for attendees
- 🌐 Embeddable widgets for external websites
- 📤 Export data in multiple formats (CSV, Excel, PDF)
- 🔄 Refund processing and order management
- 📝 Custom questions during checkout
- 🏢 Multiple organizer support

## Tech Stack

- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL
- **Authentication**: JWT with OAuth2 options
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **Hosting**: AWS or Vercel

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 16+ (for local development)
- Python 3.10+ (for local development)
- PostgreSQL (if running outside Docker)

### Installation with Docker

1. Clone the repository

   ```bash
   git clone https://github.com/yourusername/EventTicketing.git
   cd EventTicketing
   ```
2. Copy the environment template files

   ```bash
   cp frontend/.env.example frontend/.env.local
   cp backend/.env.example backend/.env
   ```
3. Start the application with Docker Compose

   ```bash
   docker-compose up -d
   ```
4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development

#### Backend Setup

1. Navigate to the backend directory

   ```bash
   cd backend
   ```
2. Create a virtual environment

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment file and configure it

   ```bash
   cp .env.example .env
   ```
5. Run migrations

   ```bash
   alembic upgrade head
   ```
6. Start the development server

   ```bash
   uvicorn app.main:app --reload
   ```

#### Frontend Setup

1. Navigate to the frontend directory

   ```bash
   cd frontend
   ```
2. Install dependencies

   ```bash
   npm install
   ```
3. Copy the environment file and configure it

   ```bash
   cp .env.example .env.local
   ```
4. Start the development server

   ```bash
   npm run dev
   ```

## Project Structure

The project is divided into two main parts:

- `frontend/`: Next.js application
- `backend/`: FastAPI application

For more details on the codebase structure, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) to get started.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- Inspired by [Attendize](https://github.com/Attendize/Attendize)
- Built with [FastAPI](https://fastapi.tiangolo.com/) and [Next.js](https://nextjs.org/)