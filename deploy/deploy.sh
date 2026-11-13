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
# Free space before building: the build cache is never reused (images are
# built with --no-cache) and previously grew to ~15 GB on the server.
docker builder prune -af > /dev/null 2>&1 || true
docker compose -f docker-compose.prod.yml build --no-cache api celery celery-beat || {
    echo -e "${RED}Error: Failed to build images${NC}"
    exit 1
}
echo -e "${GREEN}✓ Application built${NC}"

echo ""
echo -e "${BLUE}[4/7] Checking SSL certificates and configuring Nginx...${NC}"
# Verify nginx config files exist
if [ ! -f "$APP_DIR/nginx/data.goholiday.id.http-only.conf" ]; then
    echo -e "${RED}Error: HTTP-only nginx config not found!${NC}"
    exit 1
fi

# Check if SSL certificates exist
if [ -f "$APP_DIR/nginx/ssl/data.goholiday.id/fullchain.pem" ] && \
   [ -f "$APP_DIR/nginx/ssl/data.goholiday.id/privkey.pem" ] && \
   [ -f "$APP_DIR/nginx/ssl/data.goholiday.id/chain.pem" ]; then
    echo "  ✓ SSL certificates found, using SSL configuration"
    # Verify SSL config file exists
    if [ ! -f "$APP_DIR/nginx/data.goholiday.id.conf" ]; then
        echo -e "${RED}Error: SSL nginx config not found!${NC}"
        exit 1
    fi
    # Ensure SSL config is active
    if ! grep -q "./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro" docker-compose.prod.yml || \
       grep -q "# - ./nginx/data.goholiday.id.conf" docker-compose.prod.yml; then
        echo "  → Switching to SSL configuration..."
        sed -i 's|# - ./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|- ./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|g' docker-compose.prod.yml
        sed -i 's|# - ./nginx/ssl:/etc/nginx/ssl:ro|- ./nginx/ssl:/etc/nginx/ssl:ro|g' docker-compose.prod.yml
        sed -i 's|- ./nginx/data.goholiday.id.http-only.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|# - ./nginx/data.goholiday.id.http-only.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|g' docker-compose.prod.yml
    fi
else
    echo "  ⚠ SSL certificates not found, using HTTP-only configuration"
    # Ensure HTTP-only config is active
    if ! grep -q "./nginx/data.goholiday.id.http-only.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro" docker-compose.prod.yml || \
       grep -q "# - ./nginx/data.goholiday.id.http-only.conf" docker-compose.prod.yml; then
        echo "  → Switching to HTTP-only configuration..."
        sed -i 's|# - ./nginx/data.goholiday.id.http-only.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|- ./nginx/data.goholiday.id.http-only.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|g' docker-compose.prod.yml
        sed -i 's|- ./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|# - ./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|g' docker-compose.prod.yml
        sed -i 's|- ./nginx/ssl:/etc/nginx/ssl:ro|# - ./nginx/ssl:/etc/nginx/ssl:ro|g' docker-compose.prod.yml
    fi
fi
echo -e "${GREEN}✓ Nginx configuration ready${NC}"

echo ""
echo -e "${BLUE}[5/7] Starting services...${NC}"
docker compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo -e "${BLUE}[6/7] Waiting for database to be ready...${NC}"
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
echo -e "${BLUE}[7/7] Running database migrations...${NC}"
if ! docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput; then
    echo -e "${RED}Error: Migrations failed${NC}"
    echo -e "${YELLOW}Showing last 30 lines of API logs:${NC}"
    docker compose -f docker-compose.prod.yml logs api | tail -30
    exit 1
fi
echo -e "${GREEN}✓ Migrations completed${NC}"

echo ""
echo -e "${BLUE}Collecting static files...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py collectstatic --noinput --clear || {
    echo -e "${YELLOW}⚠ Static files collection had warnings${NC}"
}
echo -e "${GREEN}✓ Static files collected${NC}"

echo ""
echo -e "${BLUE}Removing old Docker images and build cache...${NC}"
# Each deploy builds new images; the replaced ones become untagged and were
# never removed (~100 of them had filled ~30 GB of the disk). Only untagged
# images are removed; running and base images are kept.
docker image prune -f > /dev/null 2>&1 || true
docker builder prune -af > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Cleanup done ($(df -h / | awk 'NR==2 {print $4}') free on /)${NC}"

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

# Check nginx configuration
if docker compose -f docker-compose.prod.yml exec -T nginx nginx -t > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration error!${NC}"
    docker compose -f docker-compose.prod.yml exec -T nginx nginx -t
    exit 1
fi

# Check API health
if docker compose -f docker-compose.prod.yml exec -T api curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${YELLOW}⚠ API health check failed (may need a moment to start)${NC}"
fi

echo ""
echo -e "${GREEN}Deployment successful! 🎉${NC}"
echo ""

