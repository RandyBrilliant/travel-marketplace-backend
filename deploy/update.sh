#!/bin/bash

# Update Script
# Updates the application with new code changes
# Causes ~30-60 seconds of downtime

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
echo "Travel Marketplace - Update"
echo "==========================================${NC}"
echo ""

cd "$APP_DIR" || {
    echo -e "${RED}Error: Cannot access $APP_DIR${NC}"
    exit 1
}

# Check if services are running
if ! docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠ No services are running. Use deploy.sh instead.${NC}"
    exit 1
fi

echo -e "${YELLOW}⚠ This will cause ~30-60 seconds of downtime${NC}"
read -p "Continue? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Update cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}[1/5] Pulling latest code...${NC}"
if [ -d ".git" ]; then
    git pull || {
        echo -e "${YELLOW}⚠ Git pull had issues, continuing anyway...${NC}"
    }
    echo -e "${GREEN}✓ Code updated${NC}"
else
    echo -e "${YELLOW}⚠ Not a git repository, skipping git pull${NC}"
fi

echo ""
echo -e "${BLUE}[2/5] Stopping services...${NC}"
docker compose -f docker-compose.prod.yml down
echo -e "${GREEN}✓ Services stopped${NC}"

echo ""
echo -e "${BLUE}[3/5] Building new images...${NC}"
# Free space before building: the build cache is never reused (images are
# built with --no-cache) and previously grew to ~15 GB on the server.
docker builder prune -af > /dev/null 2>&1 || true
docker compose -f docker-compose.prod.yml build --no-cache api celery celery-beat || {
    echo -e "${RED}Error: Failed to build images${NC}"
    exit 1
}
echo -e "${GREEN}✓ Images built${NC}"

echo ""
echo -e "${BLUE}[4/5] Starting services...${NC}"
docker compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo -e "${BLUE}[5/5] Running migrations...${NC}"
# Wait for database
sleep 5
docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput || {
    echo -e "${YELLOW}⚠ Migrations had issues${NC}"
}
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
echo "✅ Update Complete!"
echo "==========================================${NC}"
echo ""

# Show service status
docker compose -f docker-compose.prod.yml ps

echo ""
echo -e "${GREEN}Update successful! 🎉${NC}"
echo ""

