#!/bin/bash

# Quick Update Script
# Use this when you've made code changes and want to deploy them

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=========================================="
echo "Quick Update Deployment"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}Working directory: $APP_DIR${NC}"
echo ""

cd "$APP_DIR" || exit 1

# Step 1: Pull latest code (optional, comment out if you upload manually)
echo -e "${YELLOW}[1/7] Pulling latest code...${NC}"
if [ -d ".git" ]; then
    git pull
    echo -e "${GREEN}✓ Code updated${NC}"
else
    echo -e "${YELLOW}Not a git repository, skipping pull${NC}"
fi

# Step 2: Stop containers
echo -e "${YELLOW}[2/7] Stopping containers...${NC}"
docker compose -f docker-compose.prod.yml down
echo -e "${GREEN}✓ Containers stopped${NC}"

# Step 3: Rebuild images (only changed layers will rebuild)
echo -e "${YELLOW}[3/7] Rebuilding Docker images...${NC}"
docker compose -f docker-compose.prod.yml build
echo -e "${GREEN}✓ Images rebuilt${NC}"

# Step 4: Start services
echo -e "${YELLOW}[4/7] Starting services...${NC}"
docker compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✓ Services started${NC}"

# Step 5: Wait for database to be ready
echo -e "${YELLOW}[5/7] Waiting for services to be ready...${NC}"
sleep 15

# Step 6: Run migrations
echo -e "${YELLOW}[6/7] Running database migrations...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput || \
    docker compose -f docker-compose.prod.yml run --rm api python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations complete${NC}"

# Step 7: Collect static files (if changed)
echo -e "${YELLOW}[7/7] Collecting static files...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py collectstatic --noinput --clear || true
echo -e "${GREEN}✓ Static files collected${NC}"

# Wait a bit for all services
sleep 5

# Show status
echo ""
echo -e "${GREEN}=========================================="
echo "Update Complete!"
echo "==========================================${NC}"
echo ""

echo "Container Status:"
docker compose -f docker-compose.prod.yml ps
echo ""

# Test health
echo "Testing API..."
if curl -f -s http://localhost/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy!${NC}"
else
    echo -e "${YELLOW}⚠ API health check pending...${NC}"
    echo "Check logs: docker compose -f docker-compose.prod.yml logs -f"
fi

echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "View logs:    docker compose -f docker-compose.prod.yml logs -f"
echo "Restart:      docker compose -f docker-compose.prod.yml restart"
echo "Status:       docker compose -f docker-compose.prod.yml ps"
echo ""

