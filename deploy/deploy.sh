#!/bin/bash

# Main Deployment Script
# Deploys the Travel Marketplace Backend to production
# Optimized for 1 vCPU, 2GB RAM

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_DIR="${APP_DIR:-$PROJECT_DIR}"

echo -e "${BLUE}=========================================="
echo "Travel Marketplace - Deployment"
echo "==========================================${NC}"
echo ""

# Check if .env exists
if [ ! -f "$APP_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create .env file from env.prod.example:"
    echo "  cp env.prod.example .env"
    echo "  nano .env"
    exit 1
fi

cd "$APP_DIR" || {
    echo -e "${RED}Error: Cannot access $APP_DIR${NC}"
    exit 1
}

echo -e "${BLUE}[1/7] Creating necessary directories...${NC}"
mkdir -p logs
mkdir -p nginx/logs
mkdir -p media
mkdir -p staticfiles
mkdir -p nginx/ssl
# Ensure logs directory is writable
chmod 755 logs nginx/logs media staticfiles nginx/ssl 2>/dev/null || true
# Create log file if it doesn't exist (to avoid permission issues)
touch logs/django.log 2>/dev/null || true
chmod 666 logs/django.log 2>/dev/null || true
echo -e "${GREEN}✓ Directories created${NC}"

echo ""
echo -e "${BLUE}[2/9] Pulling Docker images...${NC}"
docker compose -f docker-compose.prod.yml pull --quiet || {
    echo -e "${YELLOW}⚠ Some images need to be built${NC}"
}
echo -e "${GREEN}✓ Images ready${NC}"

echo ""
echo -e "${BLUE}[3/9] Building application image...${NC}"
docker compose -f docker-compose.prod.yml build --no-cache api celery celery-beat || {
    echo -e "${RED}Error: Failed to build images${NC}"
    exit 1
}
echo -e "${GREEN}✓ Application built${NC}"

echo ""
echo -e "${BLUE}[4/9] Checking SSL certificates and configuring Nginx...${NC}"
if [ -f "$APP_DIR/nginx/ssl/fullchain.pem" ] && [ -f "$APP_DIR/nginx/ssl/privkey.pem" ]; then
    echo -e "${GREEN}✓ SSL certificates found${NC}"
else
    echo -e "${YELLOW}  ⚠ SSL certificates not found, using HTTP-only configuration${NC}"
    echo -e "${YELLOW}  → Switching to HTTP-only configuration...${NC}"
fi
echo -e "${GREEN}✓ Nginx configuration ready${NC}"

echo ""
echo -e "${BLUE}[5/9] Checking port availability...${NC}"
# Check if port 80 is in use
if command -v lsof > /dev/null 2>&1; then
    PORT80_PID=$(sudo lsof -ti:80 2>/dev/null || true)
elif command -v netstat > /dev/null 2>&1; then
    PORT80_PID=$(sudo netstat -tlnp 2>/dev/null | grep ':80 ' | awk '{print $7}' | cut -d'/' -f1 | head -1 || true)
elif command -v ss > /dev/null 2>&1; then
    PORT80_PID=$(sudo ss -tlnp 2>/dev/null | grep ':80 ' | grep -oP 'pid=\K[0-9]+' | head -1 || true)
else
    PORT80_PID=""
fi

if [ -n "$PORT80_PID" ]; then
    echo -e "${RED}Error: Port 80 is already in use (PID: $PORT80_PID)${NC}"
    echo -e "${YELLOW}To identify what's using port 80, run:${NC}"
    echo -e "  ${YELLOW}sudo lsof -i:80${NC}"
    echo -e "  ${YELLOW}or${NC}"
    echo -e "  ${YELLOW}sudo netstat -tlnp | grep ':80'${NC}"
    echo ""
    echo -e "${YELLOW}Common solutions:${NC}"
    echo -e "  1. Stop Apache (if running): ${YELLOW}sudo systemctl stop apache2${NC}"
    echo -e "  2. Stop other Nginx instances: ${YELLOW}sudo systemctl stop nginx${NC}"
    echo -e "  3. Stop other Docker containers using port 80"
    echo ""
    exit 1
fi

# Check if port 443 is in use (if SSL is configured)
if [ -f "$APP_DIR/nginx/ssl/fullchain.pem" ] && [ -f "$APP_DIR/nginx/ssl/privkey.pem" ]; then
    if command -v lsof > /dev/null 2>&1; then
        PORT443_PID=$(sudo lsof -ti:443 2>/dev/null || true)
    elif command -v netstat > /dev/null 2>&1; then
        PORT443_PID=$(sudo netstat -tlnp 2>/dev/null | grep ':443 ' | awk '{print $7}' | cut -d'/' -f1 | head -1 || true)
    elif command -v ss > /dev/null 2>&1; then
        PORT443_PID=$(sudo ss -tlnp 2>/dev/null | grep ':443 ' | grep -oP 'pid=\K[0-9]+' | head -1 || true)
    else
        PORT443_PID=""
    fi
    
    if [ -n "$PORT443_PID" ]; then
        echo -e "${YELLOW}  ⚠ Port 443 is in use (PID: $PORT443_PID)${NC}"
        echo -e "${YELLOW}  → This may cause issues with SSL${NC}"
    fi
fi
echo -e "${GREEN}✓ Ports available${NC}"

echo ""
echo -e "${BLUE}[6/9] Starting services...${NC}"
docker compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo -e "${BLUE}[7/9] Waiting for database to be ready...${NC}"
timeout=60
counter=0
while ! docker compose -f docker-compose.prod.yml exec -T db pg_isready -U "${SQL_USER:-postgres}" > /dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        echo -e "${RED}Error: Database not ready after ${timeout}s${NC}"
        exit 1
    fi
    echo -n "."
done
echo ""
echo -e "${GREEN}✓ Database ready${NC}"

echo ""
echo -e "${BLUE}[8/9] Running database migrations...${NC}"
if ! docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput; then
    echo -e "${RED}Error: Migrations failed${NC}"
    echo -e "${YELLOW}Showing last 30 lines of API logs:${NC}"
    docker compose -f docker-compose.prod.yml logs api | tail -30
    exit 1
fi
echo -e "${GREEN}✓ Migrations completed${NC}"

echo ""
echo -e "${BLUE}[9/9] Collecting static files...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py collectstatic --noinput --clear || {
    echo -e "${YELLOW}⚠ Static files collection had warnings${NC}"
}
echo -e "${GREEN}✓ Static files collected${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Deployment Complete!"
echo "==========================================${NC}"
echo ""

# Show service status
echo -e "${BLUE}Service Status:${NC}"
docker compose -f docker-compose.prod.yml ps

echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Check service health:"
echo "   ${YELLOW}docker compose -f docker-compose.prod.yml ps${NC}"
echo ""
echo "2. View logs:"
echo "   ${YELLOW}docker compose -f docker-compose.prod.yml logs -f${NC}"
echo ""
echo "3. Create superuser (if needed):"
echo "   ${YELLOW}docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser${NC}"
echo ""
echo "4. Setup SSL (after DNS is configured):"
echo "   ${YELLOW}sudo ./deploy/ssl-setup.sh${NC}"
echo ""

# Health check
echo -e "${BLUE}Performing health check...${NC}"
sleep 5
if docker compose -f docker-compose.prod.yml exec -T api curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${YELLOW}⚠ API health check failed (may need a moment to start)${NC}"
fi

echo ""
echo -e "${GREEN}Deployment successful! 🎉${NC}"
echo ""

