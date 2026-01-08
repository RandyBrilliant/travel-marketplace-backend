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
chmod 755 logs nginx/logs media staticfiles nginx/ssl 2>/dev/null || true
echo -e "${GREEN}✓ Directories created${NC}"

echo ""
echo -e "${BLUE}[2/7] Pulling Docker images...${NC}"
docker compose -f docker-compose.prod.yml pull --quiet || {
    echo -e "${YELLOW}⚠ Some images need to be built${NC}"
}
echo -e "${GREEN}✓ Images ready${NC}"

echo ""
echo -e "${BLUE}[3/7] Building application image...${NC}"
docker compose -f docker-compose.prod.yml build --no-cache api celery celery-beat || {
    echo -e "${RED}Error: Failed to build images${NC}"
    exit 1
}
echo -e "${GREEN}✓ Application built${NC}"

echo ""
echo -e "${BLUE}[4/7] Starting services...${NC}"
docker compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo -e "${BLUE}[5/7] Waiting for database to be ready...${NC}"
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
echo -e "${BLUE}[6/7] Running database migrations...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput || {
    echo -e "${RED}Error: Migrations failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ Migrations completed${NC}"

echo ""
echo -e "${BLUE}[7/7] Collecting static files...${NC}"
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

