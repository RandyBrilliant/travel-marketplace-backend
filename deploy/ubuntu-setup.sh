#!/bin/bash

set -e

echo "=========================================="
echo "DCNetwork API - Ubuntu Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Update system
echo -e "${GREEN}[1/8] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

# Install required packages
echo -e "${GREEN}[2/8] Installing required packages...${NC}"
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    ufw \
    git \
    wget \
    certbot \
    python3-certbot-nginx \
    logrotate

# Install Docker
echo -e "${GREEN}[3/8] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Set up Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
    echo -e "${YELLOW}Docker is already installed${NC}"
fi

# Install Docker Compose (standalone if not using plugin)
if ! docker compose version &> /dev/null; then
    echo -e "${GREEN}Installing Docker Compose standalone...${NC}"
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo -e "${YELLOW}Docker Compose is already installed${NC}"
fi

# Configure firewall
echo -e "${GREEN}[4/8] Configuring firewall (UFW)...${NC}"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force reload

# Create application directory
echo -e "${GREEN}[5/8] Creating application directories...${NC}"
APP_DIR="/opt/dcnetwork-api"
mkdir -p $APP_DIR
mkdir -p $APP_DIR/nginx/ssl
mkdir -p $APP_DIR/nginx/logs
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/backups
mkdir -p /var/www/certbot

# Create non-root user for application (optional)
if ! id "dcnetwork-api" &>/dev/null; then
    useradd -r -s /bin/bash -d $APP_DIR dcnetwork-api
    chown -R dcnetwork-api:dcnetwork-api $APP_DIR
fi

# Setup log rotation
echo -e "${GREEN}[6/8] Setting up log rotation...${NC}"
cat > /etc/logrotate.d/dcnetwork-api << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 dcnetwork-api dcnetwork-api
    sharedscripts
    postrotate
        docker compose -f $APP_DIR/docker-compose.prod.yml restart api || true
    endscript
}
EOF

# Create systemd service
echo -e "${GREEN}[7/8] Creating systemd service...${NC}"
cat > /etc/systemd/system/dcnetwork-api.service << EOF
[Unit]
Description=DCNetwork API Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose -f $APP_DIR/docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f $APP_DIR/docker-compose.prod.yml down
TimeoutStartSec=0
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dcnetwork-api.service

# Setup cron for SSL renewal
echo -e "${GREEN}[8/8] Setting up SSL renewal cron job...${NC}"
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker compose -f $APP_DIR/docker-compose.prod.yml restart nginx'") | crontab -

echo ""
echo -e "${GREEN}=========================================="
echo "Setup completed successfully!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Copy your application files to: $APP_DIR"
echo "2. Configure your .env file in: $APP_DIR/.env"
echo "3. Point DNS for api.goholiday.id to this server's IP"
echo "4. Run: ./deploy/ssl-setup.sh to setup SSL certificate"
echo "5. Run: ./deploy/deploy.sh to deploy the application"
echo ""

