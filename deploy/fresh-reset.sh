#!/bin/bash

# Complete Fresh Reset Script
# This will completely remove ALL Docker resources and clean up all generated files
# WARNING: This will delete your database, all containers, volumes, images, and generated files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${RED}=========================================="
echo "⚠️  COMPLETE FRESH RESET ⚠️"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}This will PERMANENTLY DELETE:${NC}"
echo "  ❌ All Docker containers"
echo "  ❌ All Docker volumes (DATABASE WILL BE DELETED)"
echo "  ❌ All Docker networks"
echo "  ❌ All Docker images"
echo "  ❌ All generated files (logs, staticfiles, media, __pycache__)"
echo "  ❌ All backup files"
echo ""
echo -e "${YELLOW}This will KEEP:${NC}"
echo "  ✓ Source code"
echo "  ✓ .env file (backed up)"
echo "  ✓ Git repository"
echo ""
echo -e "${RED}THIS CANNOT BE UNDONE!${NC}"
echo ""

read -p "Type 'RESET EVERYTHING' to confirm: " confirm

if [ "$confirm" != "RESET EVERYTHING" ]; then
    echo -e "${YELLOW}Reset cancelled.${NC}"
    exit 0
fi

cd "$APP_DIR" || {
    echo -e "${RED}Error: Cannot access $APP_DIR${NC}"
    exit 1
}

echo ""
echo -e "${BLUE}=========================================="
echo "Starting Complete Reset..."
echo "==========================================${NC}"
echo ""

# Backup .env
if [ -f "$APP_DIR/.env" ]; then
    echo -e "${BLUE}[1/10] Backing up .env file...${NC}"
    cp "$APP_DIR/.env" /tmp/travel-api-env-backup-$(date +%Y%m%d-%H%M%S)
    echo -e "${GREEN}✓ .env backed up${NC}"
else
    echo -e "${YELLOW}⚠ .env file not found${NC}"
fi

# Stop all containers
echo ""
echo -e "${BLUE}[2/10] Stopping all containers...${NC}"
if [ -f "docker-compose.prod.yml" ]; then
    docker compose -f docker-compose.prod.yml down -v 2>/dev/null || true
fi
if [ -f "docker-compose.yml" ]; then
    docker compose -f docker-compose.yml down -v 2>/dev/null || true
fi
docker stop $(docker ps -aq) 2>/dev/null || echo "  No containers to stop"
echo -e "${GREEN}✓ All containers stopped${NC}"

# Remove all containers
echo ""
echo -e "${BLUE}[3/10] Removing all containers...${NC}"
docker rm -f $(docker ps -aq) 2>/dev/null || echo "  No containers to remove"
echo -e "${GREEN}✓ All containers removed${NC}"

# Remove all volumes
echo ""
echo -e "${BLUE}[4/10] Removing all Docker volumes...${NC}"
docker volume ls -q | xargs -r docker volume rm -f 2>/dev/null || true
docker volume prune -af 2>/dev/null || true
echo -e "${GREEN}✓ All volumes removed${NC}"

# Remove all networks
echo ""
echo -e "${BLUE}[5/10] Removing all Docker networks...${NC}"
docker network prune -af 2>/dev/null || true
echo -e "${GREEN}✓ All networks removed${NC}"

# Remove all images
echo ""
echo -e "${BLUE}[6/10] Removing all Docker images...${NC}"
docker rmi -f $(docker images -aq) 2>/dev/null || echo "  No images to remove"
echo -e "${GREEN}✓ All images removed${NC}"

# Clean Docker system
echo ""
echo -e "${BLUE}[7/10] Cleaning Docker system...${NC}"
docker system prune -af --volumes 2>/dev/null || true
echo -e "${GREEN}✓ Docker system cleaned${NC}"

# Remove generated files
echo ""
echo -e "${BLUE}[8/10] Removing generated files...${NC}"

# Remove Python cache
find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$APP_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$APP_DIR" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
echo "  ✓ Python cache removed"

# Remove logs
if [ -d "$APP_DIR/logs" ]; then
    rm -rf "$APP_DIR/logs"/*
    echo "  ✓ Logs cleared"
fi

# Remove staticfiles
if [ -d "$APP_DIR/staticfiles" ]; then
    rm -rf "$APP_DIR/staticfiles"/*
    echo "  ✓ Static files cleared"
fi

# Remove media (but keep directory structure)
if [ -d "$APP_DIR/media" ]; then
    find "$APP_DIR/media" -mindepth 1 -delete 2>/dev/null || true
    echo "  ✓ Media files cleared"
fi

# Remove nginx logs
if [ -d "$APP_DIR/nginx/logs" ]; then
    rm -rf "$APP_DIR/nginx/logs"/*
    echo "  ✓ Nginx logs cleared"
fi

# Remove backup files
if [ -d "$APP_DIR/backups" ]; then
    rm -rf "$APP_DIR/backups"/*
    echo "  ✓ Backup files removed"
fi

# Remove nginx backup configs
find "$APP_DIR/nginx" -name "*.backup*" -delete 2>/dev/null || true
echo "  ✓ Nginx backup configs removed"

# Remove SSL certificates (they can be regenerated)
if [ -d "$APP_DIR/nginx/ssl" ]; then
    rm -rf "$APP_DIR/nginx/ssl"/*
    echo "  ✓ SSL certificates removed (can be regenerated)"
fi

# Remove db.sqlite3 if exists
if [ -f "$APP_DIR/db.sqlite3" ]; then
    rm -f "$APP_DIR/db.sqlite3"
    echo "  ✓ SQLite database removed"
fi

echo -e "${GREEN}✓ All generated files removed${NC}"

# Remove migrations (optional - comment out if you want to keep them)
echo ""
echo -e "${BLUE}[9/10] Removing migration files...${NC}"
find "$APP_DIR" -path "*/migrations/*.py" ! -name "__init__.py" -delete 2>/dev/null || true
find "$APP_DIR" -path "*/migrations/*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Migration files removed${NC}"

# Restore .env
echo ""
echo -e "${BLUE}[10/10] Restoring .env file...${NC}"
LATEST_BACKUP=$(ls -t /tmp/travel-api-env-backup-* 2>/dev/null | head -1)
if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP" ]; then
    cp "$LATEST_BACKUP" "$APP_DIR/.env"
    echo -e "${GREEN}✓ .env restored from backup${NC}"
    echo -e "${YELLOW}  Backup location: $LATEST_BACKUP${NC}"
else
    echo -e "${YELLOW}⚠ No .env backup found${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Complete Fresh Reset Done!"
echo "==========================================${NC}"
echo ""

# Show Docker status
echo -e "${BLUE}Docker Status:${NC}"
echo "Containers: $(docker ps -aq | wc -l)"
echo "Volumes: $(docker volume ls -q | wc -l)"
echo "Networks: $(docker network ls -q | wc -l)"
echo "Images: $(docker images -q | wc -l)"
echo ""

echo -e "${BLUE}Next Steps:${NC}"
echo "1. Review your .env file: ${YELLOW}cat .env${NC}"
echo "2. Pull latest code: ${YELLOW}git pull${NC}"
echo "3. Run migrations: ${YELLOW}python manage.py makemigrations${NC}"
echo "4. Deploy: ${YELLOW}sudo ./deploy/deploy.sh${NC}"
echo ""

echo -e "${GREEN}Your environment is now completely clean! 🎉${NC}"
echo ""

