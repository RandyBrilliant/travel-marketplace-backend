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

DOMAIN="api.goholiday.id"
EMAIL="${SSL_EMAIL:-admin@goholiday.id}"

echo "=========================================="
echo "SSL Certificate Setup - Let's Encrypt"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Check if domain is reachable
echo -e "${GREEN}[1/5] Checking domain DNS...${NC}"
if ! dig +short $DOMAIN | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo -e "${RED}Error: Domain $DOMAIN does not resolve to an IP address${NC}"
    echo "Please configure DNS first:"
    echo "  A record: $DOMAIN -> Your server IP"
    exit 1
fi

SERVER_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip)
DOMAIN_IP=$(dig +short $DOMAIN | head -n1)

if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
    echo -e "${YELLOW}Warning: Domain IP ($DOMAIN_IP) does not match server IP ($SERVER_IP)${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create necessary directories
echo -e "${GREEN}[2/5] Creating directories...${NC}"
mkdir -p "$APP_DIR/nginx/ssl/$DOMAIN"
mkdir -p /var/www/certbot
chmod -R 755 /var/www/certbot

# Check if production nginx is running and stop it temporarily
echo -e "${GREEN}[3/6] Checking for running nginx containers...${NC}"
NGINX_RUNNING=false
if docker ps --format '{{.Names}}' | grep -q "dcnetwork-api-nginx"; then
    echo "Stopping production nginx temporarily..."
    docker stop dcnetwork-api-nginx
    NGINX_RUNNING=true
    sleep 2
fi

# Create temporary nginx config for certificate challenge
echo -e "${GREEN}[4/6] Creating temporary Nginx configuration...${NC}"
TEMP_NGINX_CONF="/tmp/nginx-certbot.conf"
cat > "$TEMP_NGINX_CONF" << EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}
EOF

# Clean up any existing nginx-certbot container
docker stop nginx-certbot 2>/dev/null || true
docker rm nginx-certbot 2>/dev/null || true

# Start temporary nginx container for certificate challenge
echo -e "${GREEN}[5/6] Starting temporary Nginx for certificate challenge...${NC}"
docker run -d --name nginx-certbot \
    -p 80:80 \
    -v /var/www/certbot:/var/www/certbot \
    -v "$TEMP_NGINX_CONF:/etc/nginx/conf.d/default.conf:ro" \
    nginx:alpine

sleep 2

# Request certificate
echo -e "${GREEN}[6/6] Requesting SSL certificate from Let's Encrypt...${NC}"
certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN" || {
    echo -e "${RED}Certificate request failed. Stopping temporary nginx...${NC}"
    docker stop nginx-certbot || true
    docker rm nginx-certbot || true
    rm -f "$TEMP_NGINX_CONF"
    exit 1
}

# Stop temporary nginx
docker stop nginx-certbot || true
docker rm nginx-certbot || true
rm -f "$TEMP_NGINX_CONF"

# Restart production nginx if it was running
if [ "$NGINX_RUNNING" = true ]; then
    echo -e "${GREEN}Restarting production nginx...${NC}"
    docker start dcnetwork-api-nginx || true
fi

# Copy certificates to nginx directory
echo -e "${GREEN}Copying certificates to nginx directory...${NC}"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
cp "$CERT_PATH/fullchain.pem" "$APP_DIR/nginx/ssl/$DOMAIN/fullchain.pem"
cp "$CERT_PATH/privkey.pem" "$APP_DIR/nginx/ssl/$DOMAIN/privkey.pem"
cp "$CERT_PATH/chain.pem" "$APP_DIR/nginx/ssl/$DOMAIN/chain.pem"
chmod 644 "$APP_DIR/nginx/ssl/$DOMAIN/fullchain.pem"
chmod 600 "$APP_DIR/nginx/ssl/$DOMAIN/privkey.pem"
chmod 644 "$APP_DIR/nginx/ssl/$DOMAIN/chain.pem"

# Setup auto-renewal hook
echo -e "${GREEN}Setting up certificate auto-renewal...${NC}"
RENEWAL_HOOK="/etc/letsencrypt/renewal-hooks/deploy/travel-api-nginx.sh"
mkdir -p "$(dirname "$RENEWAL_HOOK")"
cat > "$RENEWAL_HOOK" << 'EOF'
#!/bin/bash
# Copy renewed certificates
DOMAIN="api.goholiday.id"
APP_DIR="/opt/travel-marketplace-backend"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN"

cp "$CERT_PATH/fullchain.pem" "$APP_DIR/nginx/ssl/$DOMAIN/fullchain.pem"
cp "$CERT_PATH/privkey.pem" "$APP_DIR/nginx/ssl/$DOMAIN/privkey.pem"
cp "$CERT_PATH/chain.pem" "$APP_DIR/nginx/ssl/$DOMAIN/chain.pem"

# Reload nginx
docker compose -f "$APP_DIR/docker-compose.prod.yml" restart nginx || true
EOF

chmod +x "$RENEWAL_HOOK"

# Update cron job for renewal
(crontab -l 2>/dev/null | grep -v "certbot renew" || true; \
 echo "0 3 * * * certbot renew --quiet --deploy-hook '$RENEWAL_HOOK'") | crontab -

echo ""
echo -e "${GREEN}=========================================="
echo "SSL certificate setup completed!"
echo "==========================================${NC}"
echo ""
echo "Certificate location: $APP_DIR/nginx/ssl/$DOMAIN/"
echo ""
echo "Next steps:"
echo "1. Make sure your docker-compose.prod.yml is configured correctly"
echo "2. Run: ./deploy/deploy.sh to deploy the application"
echo "3. Test SSL: https://$DOMAIN"
echo ""

