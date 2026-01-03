#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_DIR="${APP_DIR:-/opt/travel-marketplace-backend}"

echo "=========================================="
echo "Travel Marketplace Backend - Deployment"
echo "=========================================="

# Check if running as root (required for /opt directory access)
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    echo "Usage: sudo ./deploy/deploy.sh"
    exit 1
fi

# Check if .env exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy env.prod.example to .env and configure it."
    exit 1
fi

# Check if running in correct directory
if [ ! -f "$PROJECT_DIR/docker-compose.prod.yml" ]; then
    echo -e "${RED}Error: docker-compose.prod.yml not found!${NC}"
    echo "Please run this script from the project root directory."
    exit 1
fi

cd "$PROJECT_DIR"

# Backup existing deployment if it exists
if [ -d "$APP_DIR" ] && [ -f "$APP_DIR/docker-compose.prod.yml" ]; then
    echo -e "${YELLOW}Creating backup of existing deployment...${NC}"
    BACKUP_DIR="$APP_DIR/backups/backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    if docker compose -f "$APP_DIR/docker-compose.prod.yml" ps db | grep -q "Up"; then
        echo -e "${GREEN}Backing up database...${NC}"
        docker compose -f "$APP_DIR/docker-compose.prod.yml" exec -T db pg_dump -U ${SQL_USER:-travel_user} ${SQL_DATABASE:-travel_marketplace} > "$BACKUP_DIR/database.sql" || true
    fi
fi

# Copy files to deployment directory
echo -e "${GREEN}[1/6] Copying files to deployment directory...${NC}"
mkdir -p "$APP_DIR"

# Ensure correct ownership of deployment directory
chown -R $SUDO_USER:$SUDO_USER "$APP_DIR" 2>/dev/null || chown -R root:root "$APP_DIR"

rsync -av --exclude='.git' \
    --exclude='env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='db.sqlite3' \
    --exclude='celerybeat-schedule' \
    "$PROJECT_DIR/" "$APP_DIR/"

# Copy .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$APP_DIR/.env"
    echo -e "${GREEN}Copied .env file${NC}"
fi

cd "$APP_DIR"

# Create necessary directories
echo -e "${GREEN}[2/6] Creating necessary directories...${NC}"
mkdir -p nginx/ssl
mkdir -p nginx/logs
mkdir -p logs
mkdir -p media/profile_photos/staff
mkdir -p media/profile_photos/supplier
mkdir -p media/profile_photos/reseller
mkdir -p backups

# Set permissions for directories that containers need to write to
chmod -R 777 logs media 2>/dev/null || true

# Set permissions
chmod +x deploy/*.sh entrypoint.sh 2>/dev/null || true

# Pull latest images
echo -e "${GREEN}[3/6] Pulling Docker images...${NC}"
docker compose -f docker-compose.prod.yml pull

# Build images
echo -e "${GREEN}[4/6] Building Docker images...${NC}"
docker compose -f docker-compose.prod.yml build --no-cache

# Stop existing containers
echo -e "${GREEN}[5/6] Stopping existing containers...${NC}"
docker compose -f docker-compose.prod.yml down || true

# Stop system nginx if running (to free port 80)
echo -e "${GREEN}Checking for services using port 80...${NC}"
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${YELLOW}Stopping system nginx service (conflicts with Docker nginx)...${NC}"
    systemctl stop nginx
    systemctl disable nginx
    echo -e "${GREEN}System nginx stopped and disabled${NC}"
elif pgrep nginx > /dev/null; then
    echo -e "${YELLOW}Stopping nginx processes...${NC}"
    pkill nginx
fi

# Note: Static volume permissions will be handled after containers start

# Start services
echo -e "${GREEN}[6/6] Starting services...${NC}"
docker compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo -e "${GREEN}Waiting for services to be healthy...${NC}"
sleep 10

# Run migrations
echo -e "${GREEN}Running database migrations...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput || \
    docker compose -f docker-compose.prod.yml run --rm api python manage.py migrate --noinput

# Collect static files (with permission fix)
echo -e "${GREEN}Collecting static files...${NC}"
# Fix permissions first if there are any permission issues (run as root)
docker compose -f docker-compose.prod.yml exec -u root -T api chown -R 1000:1000 /app/staticfiles 2>/dev/null || true
# Run collectstatic
docker compose -f docker-compose.prod.yml exec -T api python manage.py collectstatic --noinput --clear 2>&1 || {
    echo -e "${YELLOW}Permission error detected. Fixing and retrying...${NC}"
    # If it fails, try to fix permissions and run again
    docker compose -f docker-compose.prod.yml run --rm --user root api chown -R 1000:1000 /app/staticfiles || true
    docker compose -f docker-compose.prod.yml run --rm api python manage.py collectstatic --noinput --clear
}

# Restart nginx to pick up static files
docker compose -f docker-compose.prod.yml restart nginx || true

# Health check
echo -e "${GREEN}Performing health check...${NC}"
sleep 5

if curl -f -s http://localhost/health/ > /dev/null 2>&1 || \
   curl -f -s https://localhost/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}Health check passed!${NC}"
else
    echo -e "${YELLOW}Warning: Health check failed. Please check logs.${NC}"
    echo "Run: docker compose -f $APP_DIR/docker-compose.prod.yml logs"
fi

# Show status
echo ""
echo -e "${GREEN}=========================================="
echo "Deployment completed!"
echo "==========================================${NC}"
echo ""
echo "Service status:"
docker compose -f docker-compose.prod.yml ps
echo ""
echo "To view logs:"
echo "  docker compose -f $APP_DIR/docker-compose.prod.yml logs -f"
echo ""
echo "To restart services:"
echo "  docker compose -f $APP_DIR/docker-compose.prod.yml restart"
echo ""

