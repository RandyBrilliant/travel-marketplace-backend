#!/bin/bash

# Complete Docker Reset Script
# This will completely remove all containers, volumes, and networks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

APP_DIR="${APP_DIR:-/opt/travel-marketplace-backend}"

echo -e "${RED}=========================================="
echo "WARNING: Complete Docker Reset"
echo "==========================================${NC}"
echo ""
echo "This will:"
echo "  1. Stop all containers"
echo "  2. Remove all containers"
echo "  3. Remove all volumes (DATABASE WILL BE DELETED)"
echo "  4. Remove all networks"
echo "  5. Remove all images"
echo "  6. Clean up Docker system"
echo ""
echo -e "${YELLOW}Make sure you have a backup before proceeding!${NC}"
echo ""

read -p "Are you absolutely sure? Type 'yes' to continue: " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Reset cancelled.${NC}"
    exit 0
fi

cd "$APP_DIR" 2>/dev/null || {
    echo -e "${YELLOW}App directory not found, continuing with global cleanup...${NC}"
}

echo ""
echo -e "${BLUE}[1/7] Stopping all containers...${NC}"
if [ -f "docker-compose.prod.yml" ]; then
    docker compose -f docker-compose.prod.yml down -v || true
fi
docker stop $(docker ps -aq) 2>/dev/null || echo "No containers to stop"

echo ""
echo -e "${BLUE}[2/7] Removing all containers...${NC}"
docker rm $(docker ps -aq) 2>/dev/null || echo "No containers to remove"

echo ""
echo -e "${BLUE}[3/7] Removing all volumes...${NC}"
docker volume prune -f

echo ""
echo -e "${BLUE}[4/7] Removing all networks...${NC}"
docker network prune -f

echo ""
echo -e "${BLUE}[5/7] Removing all images...${NC}"
docker rmi $(docker images -q) -f 2>/dev/null || echo "No images to remove"

echo ""
echo -e "${BLUE}[6/7] Cleaning up Docker system...${NC}"
docker system prune -af --volumes

echo ""
echo -e "${BLUE}[7/7] Removing app directory contents (keeping .env)...${NC}"
if [ -d "$APP_DIR" ]; then
    # Backup .env if it exists
    if [ -f "$APP_DIR/.env" ]; then
        cp "$APP_DIR/.env" /tmp/travel-api-env-backup
        echo -e "${GREEN}Backed up .env to /tmp/travel-api-env-backup${NC}"
    fi
    
    # Remove everything except backups
    find "$APP_DIR" -mindepth 1 -maxdepth 1 ! -name 'backups' -exec rm -rf {} + 2>/dev/null || true
    
    # Restore .env
    if [ -f "/tmp/travel-api-env-backup" ]; then
        cp /tmp/travel-api-env-backup "$APP_DIR/.env"
        echo -e "${GREEN}Restored .env${NC}"
    fi
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Docker Reset Complete!"
echo "==========================================${NC}"
echo ""
echo "Docker Status:"
docker ps -a
echo ""
docker volume ls
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Make sure your code is up to date"
echo "2. Configure .env file"
echo "3. Run: sudo ./deploy/deploy.sh"
echo ""

