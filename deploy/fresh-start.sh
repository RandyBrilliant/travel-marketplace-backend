#!/bin/bash

# Quick Start Script - Run this after complete reset
# This automates the entire deployment process

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get current directory (where the script is run from)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=========================================="
echo "Travel Marketplace - Fresh Deployment"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}Working directory: $APP_DIR${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Step 1: Check .env exists
echo -e "${YELLOW}[Step 1/6] Checking .env file...${NC}"
if [ ! -f "$APP_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Creating from template..."
    cp "$APP_DIR/env.prod.example" "$APP_DIR/.env"
    echo -e "${YELLOW}Please edit $APP_DIR/.env with your settings${NC}"
    echo "Then run this script again."
    exit 1
fi

# Check critical env vars
echo -e "${GREEN}✓ .env file exists${NC}"

# Step 2: Verify SECURE_SSL_REDIRECT is false
echo -e "${YELLOW}[Step 2/6] Checking SSL redirect settings...${NC}"
if grep -q "SECURE_SSL_REDIRECT=true" "$APP_DIR/.env"; then
    echo -e "${YELLOW}Fixing SECURE_SSL_REDIRECT...${NC}"
    sed -i 's/SECURE_SSL_REDIRECT=true/SECURE_SSL_REDIRECT=false/' "$APP_DIR/.env"
fi
if ! grep -q "SECURE_SSL_REDIRECT" "$APP_DIR/.env"; then
    echo "SECURE_SSL_REDIRECT=false" >> "$APP_DIR/.env"
fi
echo -e "${GREEN}✓ SSL redirect configured correctly${NC}"

# Step 3: Make sure nginx config is fixed
echo -e "${YELLOW}[Step 3/6] Verifying nginx configuration...${NC}"
RESOLVER_COUNT=$(grep -c "resolver " "$APP_DIR/nginx/api.goholiday.id.conf" || echo "0")
if [ "$RESOLVER_COUNT" -gt "1" ]; then
    echo -e "${RED}Error: Multiple resolver directives found in nginx config${NC}"
    echo "Please fix nginx/api.goholiday.id.conf"
    exit 1
fi
echo -e "${GREEN}✓ Nginx configuration looks good${NC}"

# Step 4: Run deployment
echo -e "${YELLOW}[Step 4/6] Running deployment script...${NC}"
cd "$APP_DIR"
./deploy/deploy.sh

# Step 5: Wait for services
echo -e "${YELLOW}[Step 5/6] Waiting for all services to be healthy...${NC}"
sleep 30

# Step 6: Final checks
echo -e "${YELLOW}[Step 6/6] Running final checks...${NC}"

echo ""
echo "Container Status:"
docker compose -f docker-compose.prod.yml ps
echo ""

echo "Testing API endpoint..."
if curl -f -s http://localhost/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is responding!${NC}"
else
    echo -e "${RED}✗ API health check failed${NC}"
    echo "Check logs: docker compose -f $APP_DIR/docker-compose.prod.yml logs"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Deployment Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Create superuser:"
echo "   docker compose -f $APP_DIR/docker-compose.prod.yml exec api python manage.py createsuperuser"
echo ""
echo "2. Test your API:"
echo "   https://api.goholiday.id/health/"
echo "   https://api.goholiday.id/api/schema/"
echo ""
echo "3. View logs:"
echo "   docker compose -f $APP_DIR/docker-compose.prod.yml logs -f"
echo ""

