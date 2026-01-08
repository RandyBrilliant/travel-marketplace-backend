#!/bin/bash

# Database Reset Script for Docker Production
# This script resets the database by dropping all tables and running migrations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="${APP_DIR:-/opt/travel-marketplace-backend}"

echo -e "${BLUE}=========================================="
echo "Database Reset Script"
echo "==========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}Note: Running without sudo. Some operations may require root.${NC}"
fi

# Check if .env exists
if [ ! -f "$DEPLOYMENT_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found at $DEPLOYMENT_DIR/.env${NC}"
    echo "Please make sure you're running this from the correct location."
    exit 1
fi

# Load environment variables
source "$DEPLOYMENT_DIR/.env" 2>/dev/null || {
    echo -e "${YELLOW}Warning: Could not source .env file. Will use docker-compose environment.${NC}"
}

# Check if docker-compose.prod.yml exists
if [ ! -f "$DEPLOYMENT_DIR/docker-compose.prod.yml" ]; then
    echo -e "${RED}Error: docker-compose.prod.yml not found at $DEPLOYMENT_DIR${NC}"
    exit 1
fi

cd "$DEPLOYMENT_DIR"

# Check if containers are running
if ! docker compose -f docker-compose.prod.yml ps db | grep -q "Up"; then
    echo -e "${RED}Error: Database container is not running!${NC}"
    echo "Please start the containers first:"
    echo "  docker compose -f $DEPLOYMENT_DIR/docker-compose.prod.yml up -d"
    exit 1
fi

echo -e "${RED}=========================================="
echo "WARNING: Database Reset"
echo "==========================================${NC}"
echo ""
echo "This will:"
echo "  1. Backup the current database (optional)"
echo "  2. Drop all database tables"
echo "  3. Run migrations to recreate the schema"
echo "  4. Optionally create a superuser"
echo ""
echo -e "${YELLOW}ALL DATA IN THE DATABASE WILL BE LOST!${NC}"
echo ""

read -p "Do you want to create a backup first? (y/n): " backup_choice
if [ "$backup_choice" = "y" ] || [ "$backup_choice" = "Y" ]; then
    BACKUP_DIR="$DEPLOYMENT_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/database-backup-$(date +%Y%m%d-%H%M%S).sql"
    
    echo -e "${BLUE}Creating database backup...${NC}"
    SQL_USER=${SQL_USER:-travel_user}
    SQL_DATABASE=${SQL_DATABASE:-travel_marketplace}
    
    if docker compose -f docker-compose.prod.yml exec -T db pg_dump -U "$SQL_USER" "$SQL_DATABASE" > "$BACKUP_FILE" 2>/dev/null; then
        echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"
    else
        echo -e "${YELLOW}Warning: Backup failed, but continuing...${NC}"
    fi
fi

echo ""
read -p "Are you absolutely sure you want to reset the database? Type 'yes' to continue: " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Reset cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}[1/4] Dropping all database tables...${NC}"

# Method 1: Use Django's flush command (safer, preserves database structure)
echo -e "${YELLOW}Using Django flush command...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py flush --noinput || {
    echo -e "${YELLOW}Flush failed, trying alternative method...${NC}"
    
    # Method 2: Drop and recreate database
    SQL_USER=${SQL_USER:-travel_user}
    SQL_DATABASE=${SQL_DATABASE:-travel_marketplace}
    
    echo -e "${YELLOW}Dropping and recreating database...${NC}"
    docker compose -f docker-compose.prod.yml exec -T db psql -U "$SQL_USER" -d postgres -c "DROP DATABASE IF EXISTS $SQL_DATABASE;" || true
    docker compose -f docker-compose.prod.yml exec -T db psql -U "$SQL_USER" -d postgres -c "CREATE DATABASE $SQL_DATABASE;" || {
        echo -e "${RED}Error: Failed to recreate database${NC}"
        exit 1
    }
}

echo -e "${GREEN}✓ Database cleared${NC}"

echo ""
echo -e "${BLUE}[2/4] Running migrations...${NC}"
if docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput; then
    echo -e "${GREEN}✓ Migrations completed${NC}"
else
    echo -e "${RED}Error: Migrations failed${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}[3/4] Collecting static files...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py collectstatic --noinput --clear 2>/dev/null || {
    echo -e "${YELLOW}Warning: Static files collection had issues, but continuing...${NC}"
}
echo -e "${GREEN}✓ Static files collected${NC}"

echo ""
read -p "Do you want to create a superuser? (y/n): " create_superuser
if [ "$create_superuser" = "y" ] || [ "$create_superuser" = "Y" ]; then
    echo -e "${BLUE}[4/4] Creating superuser...${NC}"
    echo -e "${YELLOW}You will be prompted to enter username, email, and password.${NC}"
    docker compose -f docker-compose.prod.yml exec -T api python manage.py createsuperuser || {
        echo -e "${YELLOW}Superuser creation cancelled or failed.${NC}"
        echo "You can create one later with:"
        echo "  docker compose -f $DEPLOYMENT_DIR/docker-compose.prod.yml exec api python manage.py createsuperuser"
    }
else
    echo -e "${BLUE}[4/4] Skipping superuser creation${NC}"
    echo "You can create one later with:"
    echo "  docker compose -f $DEPLOYMENT_DIR/docker-compose.prod.yml exec api python manage.py createsuperuser"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Database Reset Complete!"
echo "==========================================${NC}"
echo ""
echo "Database has been reset and migrations have been applied."
echo ""
echo "Next steps:"
echo "1. Create a superuser (if not done):"
echo "   docker compose -f $DEPLOYMENT_DIR/docker-compose.prod.yml exec api python manage.py createsuperuser"
echo ""
echo "2. Restart services if needed:"
echo "   docker compose -f $DEPLOYMENT_DIR/docker-compose.prod.yml restart"
echo ""
echo "3. Check service status:"
echo "   docker compose -f $DEPLOYMENT_DIR/docker-compose.prod.yml ps"
echo ""

