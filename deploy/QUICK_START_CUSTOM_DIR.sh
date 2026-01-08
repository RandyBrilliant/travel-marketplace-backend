#!/bin/bash

# Quick Start Script for Custom Directory Setup
# This script configures deployment for: /home/regretzz/travel-marketplace-backend

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Custom Directory Setup"
echo "==========================================${NC}"
echo ""

# Get current user
CURRENT_USER=${SUDO_USER:-$(whoami)}
USER_HOME=$(eval echo ~$CURRENT_USER)
CUSTOM_DIR="$USER_HOME/travel-marketplace-backend"

echo -e "${BLUE}Detected setup:${NC}"
echo "User: $CURRENT_USER"
echo "Home: $USER_HOME"
echo "App Directory: $CUSTOM_DIR"
echo ""

# Confirm directory
if [ ! -d "$CUSTOM_DIR" ]; then
    echo -e "${RED}Error: Directory not found: $CUSTOM_DIR${NC}"
    echo ""
    read -p "Enter your actual app directory path: " CUSTOM_DIR
    
    if [ ! -d "$CUSTOM_DIR" ]; then
        echo -e "${RED}Directory still not found. Exiting.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Found directory: $CUSTOM_DIR${NC}"
echo ""

# Check if already configured
SHELL_RC="$USER_HOME/.bashrc"
if [ -f "$USER_HOME/.zshrc" ]; then
    SHELL_RC="$USER_HOME/.zshrc"
fi

if grep -q "export APP_DIR=" "$SHELL_RC" 2>/dev/null; then
    echo -e "${YELLOW}APP_DIR is already configured in $SHELL_RC${NC}"
    echo ""
    read -p "Update configuration? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Keeping existing configuration.${NC}"
        exit 0
    fi
    # Remove old APP_DIR lines
    sed -i '/export APP_DIR=/d' "$SHELL_RC"
    sed -i '/Travel Marketplace/d' "$SHELL_RC"
    sed -i '/alias tm-/d' "$SHELL_RC"
fi

# Add configuration
echo -e "${BLUE}[1/3] Adding APP_DIR to $SHELL_RC${NC}"

cat >> "$SHELL_RC" << EOF

# Travel Marketplace Configuration
export APP_DIR=$CUSTOM_DIR

# Travel Marketplace Aliases
alias tm-cd='cd \$APP_DIR'
alias tm-deploy='cd \$APP_DIR && sudo -E ./deploy/deploy.sh'
alias tm-optimize='cd \$APP_DIR && sudo -E ./deploy/optimize-2gb.sh'
alias tm-ssl='cd \$APP_DIR && sudo -E ./deploy/ssl-setup.sh'
alias tm-logs='docker compose -f \$APP_DIR/docker-compose.prod.yml logs -f'
alias tm-ps='docker compose -f \$APP_DIR/docker-compose.prod.yml ps'
alias tm-restart='docker compose -f \$APP_DIR/docker-compose.prod.yml restart'
alias tm-stop='docker compose -f \$APP_DIR/docker-compose.prod.yml down'
alias tm-start='docker compose -f \$APP_DIR/docker-compose.prod.yml up -d'
alias tm-stats='docker stats'
alias tm-backup='cd \$APP_DIR && sudo -E ./deploy/backup.sh'
alias tm-db-reset='cd \$APP_DIR && sudo -E ./deploy/reset-database.sh'
alias tm-env='nano \$APP_DIR/.env'
alias tm-health='curl http://localhost/health/'
EOF

echo -e "${GREEN}✓ Configuration added${NC}"

# Check file permissions
echo ""
echo -e "${BLUE}[2/3] Checking file permissions${NC}"

if [ ! -w "$CUSTOM_DIR" ]; then
    echo -e "${YELLOW}Fixing ownership...${NC}"
    if [ "$EUID" -eq 0 ]; then
        chown -R $CURRENT_USER:$CURRENT_USER "$CUSTOM_DIR"
        echo -e "${GREEN}✓ Ownership fixed${NC}"
    else
        echo -e "${YELLOW}Run with sudo to fix permissions:${NC}"
        echo "  sudo chown -R $CURRENT_USER:$CURRENT_USER $CUSTOM_DIR"
    fi
else
    echo -e "${GREEN}✓ Permissions OK${NC}"
fi

# Make scripts executable
if [ -d "$CUSTOM_DIR/deploy" ]; then
    chmod +x "$CUSTOM_DIR/deploy"/*.sh 2>/dev/null || true
    chmod +x "$CUSTOM_DIR/entrypoint.sh" 2>/dev/null || true
    echo -e "${GREEN}✓ Scripts are executable${NC}"
fi

# Check Docker group membership
echo ""
echo -e "${BLUE}[3/3] Checking Docker access${NC}"

if groups $CURRENT_USER | grep -q docker; then
    echo -e "${GREEN}✓ User is in docker group${NC}"
else
    echo -e "${YELLOW}User not in docker group${NC}"
    if [ "$EUID" -eq 0 ]; then
        echo -e "${YELLOW}Adding user to docker group...${NC}"
        usermod -aG docker $CURRENT_USER
        echo -e "${GREEN}✓ Added to docker group (logout/login required)${NC}"
    else
        echo -e "${YELLOW}Run with sudo to add to docker group:${NC}"
        echo "  sudo usermod -aG docker $CURRENT_USER"
        echo "  Then logout and login again"
    fi
fi

# Summary
echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Directory: $CUSTOM_DIR"
echo "  Shell RC: $SHELL_RC"
echo ""
echo -e "${BLUE}Available aliases (after reload):${NC}"
echo "  ${GREEN}tm-cd${NC}         - Go to app directory"
echo "  ${GREEN}tm-deploy${NC}     - Deploy application"
echo "  ${GREEN}tm-optimize${NC}   - Run 2GB optimization"
echo "  ${GREEN}tm-ssl${NC}        - Setup SSL certificates"
echo "  ${GREEN}tm-logs${NC}       - View container logs"
echo "  ${GREEN}tm-ps${NC}         - Container status"
echo "  ${GREEN}tm-restart${NC}    - Restart services"
echo "  ${GREEN}tm-stop${NC}       - Stop all services"
echo "  ${GREEN}tm-start${NC}      - Start all services"
echo "  ${GREEN}tm-stats${NC}      - Resource usage"
echo "  ${GREEN}tm-backup${NC}     - Backup database"
echo "  ${GREEN}tm-db-reset${NC}   - Reset database"
echo "  ${GREEN}tm-env${NC}        - Edit .env file"
echo "  ${GREEN}tm-health${NC}     - Check API health"
echo ""
echo -e "${YELLOW}⚠ Important: Reload your shell${NC}"
echo "  Run: ${BLUE}source $SHELL_RC${NC}"
echo "  Or logout and login again"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Reload shell: ${GREEN}source $SHELL_RC${NC}"
echo "  2. Optimize system: ${GREEN}tm-optimize${NC}"
echo "  3. Configure .env: ${GREEN}tm-env${NC}"
echo "  4. Deploy: ${GREEN}tm-deploy${NC}"
echo ""
echo -e "${BLUE}Full documentation:${NC}"
echo "  • $CUSTOM_DIR/deploy/CUSTOM_DIRECTORY_SETUP.md"
echo "  • $CUSTOM_DIR/deploy/REBUILD_CHECKLIST.md"
echo "  • $CUSTOM_DIR/deploy/OPTIMIZATION_GUIDE_2GB.md"
echo ""

