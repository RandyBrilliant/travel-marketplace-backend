#!/bin/bash

# Initial Server Setup Script
# Run this ONCE on a fresh Digital Ocean droplet (Ubuntu 22.04+)
# Optimized for 1 vCPU, 2GB RAM

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Travel Marketplace - Server Setup"
echo "Optimized for: 1 vCPU, 2GB RAM"
echo "==========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}[1/8] Updating system packages...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
echo -e "${GREEN}✓ System updated${NC}"

echo ""
echo -e "${BLUE}[2/8] Installing essential packages...${NC}"
apt-get install -y -qq \
    curl \
    wget \
    git \
    ufw \
    certbot \
    python3-certbot-nginx \
    htop \
    nano \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release
echo -e "${GREEN}✓ Essential packages installed${NC}"

echo ""
echo -e "${BLUE}[3/8] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    # Remove old versions
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    
    # Set up repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Start Docker
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

echo ""
echo -e "${BLUE}[4/8] Optimizing system for 2GB RAM...${NC}"

# Configure memory overcommit for Redis
if ! grep -q "vm.overcommit_memory = 1" /etc/sysctl.conf; then
    echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf
    sysctl vm.overcommit_memory=1
fi

# Reduce swappiness
if ! grep -q "vm.swappiness = 10" /etc/sysctl.conf; then
    echo "vm.swappiness = 10" >> /etc/sysctl.conf
    sysctl vm.swappiness=10
fi

# Apply sysctl settings
sysctl -p > /dev/null 2>&1
echo -e "${GREEN}✓ System optimized${NC}"

echo ""
echo -e "${BLUE}[5/8] Setting up swap space...${NC}"
if ! swapon --show | grep -q '/swapfile'; then
    # Create 2GB swap file
    fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    
    # Make permanent
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    echo -e "${GREEN}✓ 2GB swap file created${NC}"
else
    echo -e "${GREEN}✓ Swap already exists${NC}"
fi

echo ""
echo -e "${BLUE}[6/8] Configuring firewall (UFW)...${NC}"
# Allow SSH (important!)
ufw allow 22/tcp
# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp
# Enable firewall (non-interactive)
ufw --force enable
echo -e "${GREEN}✓ Firewall configured${NC}"

echo ""
echo -e "${BLUE}[7/8] Optimizing Docker for low memory...${NC}"
# Configure Docker daemon
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF
systemctl restart docker
sleep 2
echo -e "${GREEN}✓ Docker optimized${NC}"

echo ""
echo -e "${BLUE}[8/8] Creating necessary directories...${NC}"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/nginx/logs"
mkdir -p "$PROJECT_DIR/media"
chmod 755 "$PROJECT_DIR/logs" "$PROJECT_DIR/nginx/logs" "$PROJECT_DIR/media"
echo -e "${GREEN}✓ Directories created${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Server Setup Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}System Information:${NC}"
echo "  Memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "  Swap: $(free -h | awk '/^Swap:/ {print $2}')"
echo "  vCPUs: $(nproc)"
echo "  Docker: $(docker --version)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure your .env file:"
echo "   ${BLUE}cd $PROJECT_DIR${NC}"
echo "   ${BLUE}cp env.prod.example .env${NC}"
echo "   ${BLUE}nano .env${NC}"
echo ""
echo "2. Deploy the application:"
echo "   ${BLUE}sudo ./deploy/deploy.sh${NC}"
echo ""
echo -e "${GREEN}Setup complete! 🎉${NC}"
echo ""

