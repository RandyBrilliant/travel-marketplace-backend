#!/bin/bash

# Quick fix for Redis memory overcommit warning
# Run this before deploying

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Fixing Redis memory overcommit warning...${NC}"

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

# Fix Redis memory warning
if ! grep -q "vm.overcommit_memory = 1" /etc/sysctl.conf 2>/dev/null; then
    echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf
    sysctl vm.overcommit_memory=1
    echo -e "${GREEN}✓ Redis memory overcommit fixed${NC}"
else
    echo -e "${GREEN}✓ Already configured${NC}"
fi

echo ""
echo "You can now run deploy.sh"

