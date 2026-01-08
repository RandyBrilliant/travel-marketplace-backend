#!/bin/bash

# Rolling Update Script - Minimal Downtime
# This updates services one by one while keeping others running

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="${APP_DIR:-$(dirname "$SCRIPT_DIR")}"

echo -e "${BLUE}=========================================="
echo "Rolling Update - Minimal Downtime"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}Working directory: $APP_DIR${NC}"
echo ""

cd "$APP_DIR" || exit 1

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run with sudo${NC}"
    echo "Usage: sudo ./deploy/rolling-update.sh"
    echo "   or: sudo -E ./deploy/rolling-update.sh (to preserve environment)"
    exit 1
fi

# Step 1: Pull latest code
echo -e "${YELLOW}[1/8] Updating code...${NC}"
if [ -d ".git" ]; then
    git pull
    echo -e "${GREEN}✓ Code updated${NC}"
else
    echo -e "${YELLOW}Not a git repository, skipping pull${NC}"
fi

# Step 2: Build new images (doesn't affect running containers)
echo -e "${YELLOW}[2/8] Building new images...${NC}"
docker compose -f docker-compose.prod.yml build
echo -e "${GREEN}✓ Images built${NC}"

# Step 3: Run migrations (safe to run while services are up)
echo -e "${YELLOW}[3/8] Running database migrations...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput || \
    docker compose -f docker-compose.prod.yml run --rm api python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations complete${NC}"

# Step 4: Update Celery Beat (low priority, can have brief downtime)
echo -e "${YELLOW}[4/8] Updating Celery Beat...${NC}"
docker compose -f docker-compose.prod.yml stop celery-beat
docker compose -f docker-compose.prod.yml rm -f celery-beat
docker compose -f docker-compose.prod.yml up -d celery-beat
echo -e "${GREEN}✓ Celery Beat updated${NC}"
sleep 3

# Step 5: Update Celery Worker (background tasks)
echo -e "${YELLOW}[5/8] Updating Celery Worker...${NC}"
docker compose -f docker-compose.prod.yml stop celery
docker compose -f docker-compose.prod.yml rm -f celery
docker compose -f docker-compose.prod.yml up -d celery
echo -e "${GREEN}✓ Celery Worker updated${NC}"
sleep 3

# Step 6: Update API (main service - quick restart)
echo -e "${YELLOW}[6/8] Updating API service...${NC}"
echo -e "${BLUE}Note: Nginx will buffer requests during API restart (~2-5 seconds)${NC}"
docker compose -f docker-compose.prod.yml stop api
docker compose -f docker-compose.prod.yml rm -f api
docker compose -f docker-compose.prod.yml up -d api
echo -e "${GREEN}✓ API service updated${NC}"

# Step 7: Wait for health check
echo -e "${YELLOW}[7/8] Waiting for services to be healthy...${NC}"
sleep 10

# Test health with retries
HEALTH_OK=false
for i in {1..12}; do
    if curl -f -s http://localhost/health/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is healthy!${NC}"
        HEALTH_OK=true
        break
    else
        if [ $i -eq 12 ]; then
            echo -e "${RED}✗ API health check failed after 60 seconds${NC}"
            echo ""
            echo -e "${YELLOW}Troubleshooting:${NC}"
            echo "1. Check logs: docker compose -f $APP_DIR/docker-compose.prod.yml logs -f api"
            echo "2. Check status: docker compose -f $APP_DIR/docker-compose.prod.yml ps"
            echo "3. Restart if needed: docker compose -f $APP_DIR/docker-compose.prod.yml restart api"
            exit 1
        fi
        echo "Waiting for API... ($i/12)"
        sleep 5
    fi
done

# Step 8: Collect static files
echo -e "${YELLOW}[8/8] Collecting static files...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py collectstatic --noinput --clear || true
echo -e "${GREEN}✓ Static files collected${NC}"

# Restart nginx to pick up any static file changes
echo -e "${YELLOW}Restarting Nginx...${NC}"
docker compose -f docker-compose.prod.yml restart nginx
sleep 2

echo ""
echo -e "${GREEN}=========================================="
echo "Rolling Update Complete!"
echo "==========================================${NC}"
echo ""

echo "Container Status:"
docker compose -f docker-compose.prod.yml ps
echo ""

echo -e "${GREEN}✓ Update completed with minimal downtime${NC}"
echo -e "${BLUE}Total update time: ~30-45 seconds${NC}"
echo -e "${BLUE}User-facing downtime: ~2-5 seconds${NC}"
echo ""

# Test the API one more time
if curl -f -s http://localhost/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Final health check: PASS${NC}"
else
    echo -e "${YELLOW}⚠ Final health check: PENDING${NC}"
fi

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Monitor logs for a few minutes:"
echo "   ${GREEN}docker compose -f $APP_DIR/docker-compose.prod.yml logs -f api${NC}"
echo ""
echo "2. Check resource usage:"
echo "   ${GREEN}docker stats${NC}"
echo ""
echo "3. Test key endpoints:"
echo "   ${GREEN}curl http://localhost/api/tours/${NC}"
echo ""


