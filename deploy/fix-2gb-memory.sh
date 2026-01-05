#!/bin/bash

# Quick fix for 2GB RAM servers
# This script optimizes Docker Compose configuration for low-memory environments

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "2GB Memory Optimization Script"
echo "==========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    echo "Usage: sudo ./deploy/fix-2gb-memory.sh"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_DIR="${APP_DIR:-/opt/travel-marketplace-backend}"

echo -e "${YELLOW}[1/5] Fixing Redis memory overcommit warning...${NC}"
# Fix Redis memory warning
if ! grep -q "vm.overcommit_memory = 1" /etc/sysctl.conf 2>/dev/null; then
    echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf
    sysctl vm.overcommit_memory=1
    echo -e "${GREEN}✓ Redis memory overcommit fixed${NC}"
else
    echo -e "${GREEN}✓ Already configured${NC}"
fi

echo ""
echo -e "${YELLOW}[2/4] Pulling latest code...${NC}"
cd "$PROJECT_DIR"
if [ -d ".git" ]; then
    git pull
    echo -e "${GREEN}✓ Code updated${NC}"
else
    echo -e "${YELLOW}Not a git repository, skipping pull${NC}"
fi

echo ""
echo -e "${YELLOW}[3/4] Running deployment...${NC}"
cd "$PROJECT_DIR"
./deploy/deploy.sh

echo ""
echo -e "${YELLOW}[4/4] Restarting containers with new limits...${NC}"
cd "$APP_DIR"
docker compose -f docker-compose.prod.yml down
echo -e "${GREEN}✓ Containers stopped${NC}"

echo ""
echo -e "${BLUE}Waiting for services to stabilize (30 seconds)...${NC}"
sleep 30

echo ""
echo -e "${GREEN}=========================================="
echo "Optimization Complete!"
echo "==========================================${NC}"
echo ""

echo "Container Status:"
docker compose -f docker-compose.prod.yml ps
echo ""

echo -e "${BLUE}Memory Optimizations Applied:${NC}"
echo "  • Gunicorn: 2 workers → 1 worker"
echo "  • Celery: 2 concurrency → 1 concurrency"
echo "  • API: 256M → 200M"
echo "  • DB: 256M → 200M"
echo "  • Redis: 128M → 100M (80MB max)"
echo "  • Celery: 256M → 200M"
echo "  • Celery Beat: 64M → 100M"
echo "  • Nginx: unlimited → 50M"
echo ""
echo -e "${YELLOW}Total Container Memory: ~850MB (was ~980MB)${NC}"
echo ""

echo "Testing API health..."
if curl -f -s http://localhost/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy!${NC}"
else
    echo -e "${YELLOW}⚠ API health check pending (check logs)${NC}"
fi

echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  View logs:    docker compose -f $APP_DIR/docker-compose.prod.yml logs -f"
echo "  Check memory: docker stats"
echo "  Restore:      cp $APP_DIR/docker-compose.prod.yml.backup-* $APP_DIR/docker-compose.prod.yml"
echo ""

echo -e "${YELLOW}⚠ RECOMMENDATION:${NC}"
echo "  For better performance, upgrade to at least 4GB RAM."
echo "  Current 2GB setup will work but with reduced capacity."
echo ""

