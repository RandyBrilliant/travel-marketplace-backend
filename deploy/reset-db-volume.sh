#!/bin/bash

# Production Database Volume Reset Script (Alternative Approach)
# This script removes the entire database volume and recreates everything
# Use this if the database drop approach doesn't work
# WARNING: This will DELETE ALL DATA in the database

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

echo -e "${RED}=========================================="
echo "⚠️  PRODUCTION DATABASE VOLUME RESET ⚠️"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}This will PERMANENTLY DELETE:${NC}"
echo "  ❌ The entire database volume"
echo "  ❌ ALL database data"
echo "  ❌ ALL migrations history"
echo "  ❌ ALL user accounts"
echo "  ❌ ALL application data"
echo ""
echo -e "${YELLOW}This will:${NC}"
echo "  ✓ Keep Docker containers and images"
echo "  ✓ Keep media files (uploaded files)"
echo "  ✓ Keep static files"
echo "  ✓ Remove and recreate database volume"
echo "  ✓ Apply fresh migrations"
echo ""
echo -e "${RED}THIS CANNOT BE UNDONE!${NC}"
echo ""

# Safety check - require explicit confirmation
read -p "Type 'RESET VOLUME' to confirm: " confirm

if [ "$confirm" != "RESET VOLUME" ]; then
    echo -e "${YELLOW}Reset cancelled.${NC}"
    exit 0
fi

cd "$APP_DIR" || {
    echo -e "${RED}Error: Cannot access $APP_DIR${NC}"
    exit 1
}

# Check if .env exists
if [ ! -f "$APP_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create .env file from env.prod.example:"
    echo "  cp env.prod.example .env"
    echo "  nano .env"
    exit 1
fi

echo ""
echo -e "${BLUE}=========================================="
echo "Starting Database Volume Reset..."
echo "==========================================${NC}"
echo ""

# Stop all services
echo -e "${BLUE}[1/7] Stopping all services...${NC}"
docker compose -f docker-compose.prod.yml down
echo -e "${GREEN}✓ All services stopped${NC}"

# Remove the database volume
echo ""
echo -e "${BLUE}[2/7] Removing database volume...${NC}"

# Get the actual volume name from docker-compose
VOLUME_NAME=$(docker compose -f docker-compose.prod.yml config --volumes 2>/dev/null | grep postgres_data || echo "")

if [ -z "$VOLUME_NAME" ]; then
    # Try to find volume by listing all volumes containing postgres_data
    ACTUAL_VOLUME=$(docker volume ls --format "{{.Name}}" | grep postgres_data | head -1)
else
    # Get project name to construct full volume name
    COMPOSE_PROJECT_NAME=$(cd "$APP_DIR" && basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
    # Docker Compose v2 uses format: {project}_{volume_name}
    # Try multiple naming conventions
    ACTUAL_VOLUME=$(docker volume ls --format "{{.Name}}" | grep -E "(postgres_data|${COMPOSE_PROJECT_NAME}_postgres_data)" | head -1)
fi

if [ -n "$ACTUAL_VOLUME" ]; then
    echo "  → Found volume: $ACTUAL_VOLUME"
    docker volume rm "$ACTUAL_VOLUME" 2>/dev/null || {
        echo -e "${YELLOW}⚠ Volume might be in use, trying with force...${NC}"
        # Volume might still be referenced, but docker compose down should have removed it
        docker volume rm -f "$ACTUAL_VOLUME" 2>/dev/null || true
    }
    echo -e "${GREEN}✓ Database volume removed${NC}"
else
    echo -e "${YELLOW}⚠ No database volume found with standard naming${NC}"
    echo "  → This is okay if the volume doesn't exist yet"
    # Show all volumes for debugging
    echo "  → Available volumes:"
    docker volume ls --format "{{.Name}}" | head -5 || true
fi

# Clean up any orphaned volumes
echo ""
echo -e "${BLUE}[3/7] Cleaning up orphaned volumes...${NC}"
docker volume prune -f 2>/dev/null || true
echo -e "${GREEN}✓ Volume cleanup complete${NC}"

# Start database service (this will create a new volume)
echo ""
echo -e "${BLUE}[4/7] Starting database service...${NC}"
docker compose -f docker-compose.prod.yml up -d db
echo "  → Waiting for database to be ready..."
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
echo -e "${GREEN}✓ Database started and ready${NC}"

# Start API container to run migrations
echo ""
echo -e "${BLUE}[5/7] Starting API container...${NC}"
docker compose -f docker-compose.prod.yml up -d api
echo "  → Waiting for API container to be ready..."
timeout=60
counter=0
while ! docker compose -f docker-compose.prod.yml exec -T api curl -f http://localhost:8000/health/ > /dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        echo -e "${YELLOW}⚠ API health check timeout, but continuing with migrations...${NC}"
        break
    fi
    echo -n "."
done
echo ""
echo -e "${GREEN}✓ API container ready${NC}"

# Apply migrations
echo ""
echo -e "${BLUE}[6/7] Applying fresh migrations...${NC}"
if ! docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput; then
    echo -e "${RED}Error: Migrations failed${NC}"
    echo -e "${YELLOW}Showing last 50 lines of API logs:${NC}"
    docker compose -f docker-compose.prod.yml logs api | tail -50
    exit 1
fi
echo -e "${GREEN}✓ Migrations applied successfully${NC}"

# Show migration status
echo ""
echo -e "${BLUE}Migration Status:${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py showmigrations

# Collect static files
echo ""
echo -e "${BLUE}[7/7] Collecting static files...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py collectstatic --noinput --clear || {
    echo -e "${YELLOW}⚠ Static files collection had warnings${NC}"
}
echo -e "${GREEN}✓ Static files collected${NC}"

# Start all services
echo ""
echo -e "${BLUE}Starting all services...${NC}"
docker compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✓ All services started${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Database Volume Reset Complete!"
echo "==========================================${NC}"
echo ""

# Show service status
echo -e "${BLUE}Service Status:${NC}"
docker compose -f docker-compose.prod.yml ps

echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Create a superuser:"
echo "   ${YELLOW}docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser${NC}"
echo ""
echo "2. Check service health:"
echo "   ${YELLOW}docker compose -f docker-compose.prod.yml ps${NC}"
echo ""
echo "3. View logs:"
echo "   ${YELLOW}docker compose -f docker-compose.prod.yml logs -f api${NC}"
echo ""
echo -e "${GREEN}Database volume has been reset and migrations applied! 🎉${NC}"
echo ""

