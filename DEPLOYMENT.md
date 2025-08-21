# Deployment Guide for Raspberry Pi 4

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nodesyn/EventTicketing.git
   cd EventTicketing
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   nano .env
   ```

3. **Deploy with Docker:**
   ```bash
   # Development mode
   docker-compose up -d
   
   # Production mode
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Environment Setup

### Required Environment Variables

Edit `.env` file with your values:

- `POSTGRES_PASSWORD`: Strong password for PostgreSQL
- `JWT_SECRET`: 32+ character secret for JWT tokens
- `API_URL`: Your server's IP address (e.g., `http://192.168.1.100:8001`)

### Optional Configuration

- **Stripe**: Add your Stripe keys for payment processing
- **Email**: Configure SMTP for notifications
- **Domain**: Set production domain for CORS

## Production Deployment

### For Raspberry Pi 4:

1. **Update system:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Docker:**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

3. **Install Docker Compose:**
   ```bash
   sudo apt install docker-compose-plugin
   ```

4. **Deploy:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Access Points

- **Frontend**: http://your-pi-ip:3001
- **Backend API**: http://your-pi-ip:8001
- **API Docs**: http://your-pi-ip:8001/docs
- **PgAdmin**: http://your-pi-ip:5051 (admin@admin.com / admin)
- **PostgreSQL**: Port 5435
- **Redis**: Port 6381

## Monitoring

Check service status:
```bash
docker-compose ps
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Troubleshooting

### Common Issues:

1. **Permission denied**: Ensure user is in docker group and logout/login
2. **Port conflicts**: Check if ports 3001, 8001, 5435, 6381, 5051 are available
3. **Memory issues**: Raspberry Pi 4 needs at least 4GB RAM for full stack

### Debug Commands:
```bash
# Check container logs
docker-compose logs [service-name]

# Access container shell
docker-compose exec backend bash
docker-compose exec frontend sh

# Restart services
docker-compose restart
```

## Security Notes

- Change default passwords in `.env`
- Use strong JWT secret (32+ characters)
- Consider setting up SSL/HTTPS for production
- Regularly update Docker images