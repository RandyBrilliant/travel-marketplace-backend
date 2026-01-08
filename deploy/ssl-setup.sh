#!/bin/bash

# SSL Certificate Setup Script
# Sets up Let's Encrypt SSL certificate for data.goholiday.id

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

echo -e "${BLUE}=========================================="
echo "SSL Certificate Setup"
echo "==========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Domain configuration
DOMAIN="data.goholiday.id"
EMAIL="${SSL_EMAIL:-admin@goholiday.id}"

echo -e "${YELLOW}Domain: ${DOMAIN}${NC}"
echo -e "${YELLOW}Email: ${EMAIL}${NC}"
echo ""

# Check if DNS is configured
echo -e "${BLUE}[1/6] Checking DNS configuration...${NC}"
SERVER_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip)
DNS_IP=$(dig +short $DOMAIN | tail -n1)

if [ -z "$DNS_IP" ]; then
    echo -e "${RED}Error: DNS not configured for $DOMAIN${NC}"
    echo "Please configure an A record pointing to: $SERVER_IP"
    exit 1
fi

if [ "$DNS_IP" != "$SERVER_IP" ]; then
    echo -e "${YELLOW}⚠ Warning: DNS IP ($DNS_IP) doesn't match server IP ($SERVER_IP)${NC}"
    read -p "Continue anyway? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    echo -e "${GREEN}✓ DNS configured correctly${NC}"
fi

# Check if services are running
echo ""
echo -e "${BLUE}[2/6] Checking if services are running...${NC}"
if ! docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo -e "${RED}Error: Services are not running!${NC}"
    echo "Please run: sudo ./deploy/deploy.sh first"
    exit 1
fi
echo -e "${GREEN}✓ Services are running${NC}"

# Ensure nginx is using HTTP-only config
echo ""
echo -e "${BLUE}[3/6] Ensuring Nginx is in HTTP mode...${NC}"
cd "$APP_DIR"
# Check current nginx config
if grep -q "data.goholiday.id.http-only.conf" docker-compose.prod.yml; then
    echo -e "${GREEN}✓ Nginx is already in HTTP mode${NC}"
else
    echo -e "${YELLOW}⚠ Switching Nginx to HTTP mode...${NC}"
    # This should already be set, but just in case
    docker compose -f docker-compose.prod.yml restart nginx
    sleep 3
fi

# Stop nginx container temporarily for certbot
echo ""
echo -e "${BLUE}[4/6] Temporarily stopping Nginx for certificate generation...${NC}"
docker compose -f docker-compose.prod.yml stop nginx

# Create directory for certbot webroot
mkdir -p /var/www/certbot

# Generate certificate
echo ""
echo -e "${BLUE}[5/6] Generating SSL certificate...${NC}"
certbot certonly \
    --standalone \
    --preferred-challenges http \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive \
    --keep-until-expiring || {
    echo -e "${RED}Error: Certificate generation failed${NC}"
    echo "Common issues:"
    echo "  - DNS not pointing to this server"
    echo "  - Port 80 not accessible"
    echo "  - Too many certificate requests (Let's Encrypt rate limit)"
    docker compose -f docker-compose.prod.yml start nginx
    exit 1
}

# Copy certificates to nginx directory
echo ""
echo -e "${BLUE}[6/6] Copying certificates...${NC}"
mkdir -p "$APP_DIR/nginx/ssl/$DOMAIN"
cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$APP_DIR/nginx/ssl/$DOMAIN/fullchain.pem"
cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$APP_DIR/nginx/ssl/$DOMAIN/privkey.pem"
cp "/etc/letsencrypt/live/$DOMAIN/chain.pem" "$APP_DIR/nginx/ssl/$DOMAIN/chain.pem"
chmod 644 "$APP_DIR/nginx/ssl/$DOMAIN/fullchain.pem"
chmod 644 "$APP_DIR/nginx/ssl/$DOMAIN/chain.pem"
chmod 600 "$APP_DIR/nginx/ssl/$DOMAIN/privkey.pem"
echo -e "${GREEN}✓ Certificates copied${NC}"

# Update docker-compose.prod.yml to use SSL config
echo ""
echo -e "${BLUE}Updating Docker Compose configuration for SSL...${NC}"
cd "$APP_DIR"

# Switch to SSL config in docker-compose.prod.yml
# First, comment out HTTP-only config
sed -i 's|- ./nginx/data.goholiday.id.http-only.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|# - ./nginx/data.goholiday.id.http-only.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|g' docker-compose.prod.yml

# Then, uncomment and add SSL config
if ! grep -q "./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro" docker-compose.prod.yml || \
   grep -q "# - ./nginx/data.goholiday.id.conf" docker-compose.prod.yml; then
    # Add SSL config line (uncomment or add)
    sed -i 's|# - ./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|- ./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro|g' docker-compose.prod.yml
    # If it doesn't exist, add it after the HTTP-only line
    if ! grep -q "./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro" docker-compose.prod.yml; then
        sed -i '/# - .\/nginx\/data.goholiday.id.http-only.conf/a\      - ./nginx/data.goholiday.id.conf:/etc/nginx/conf.d/data.goholiday.id.conf:ro' docker-compose.prod.yml
    fi
fi

# Uncomment SSL volume
sed -i 's|# - ./nginx/ssl:/etc/nginx/ssl:ro|- ./nginx/ssl:/etc/nginx/ssl:ro|g' docker-compose.prod.yml
# If it doesn't exist, add it
if ! grep -q "./nginx/ssl:/etc/nginx/ssl:ro" docker-compose.prod.yml; then
    sed -i '/- .\/nginx\/data.goholiday.id.conf/a\      - ./nginx/ssl:/etc/nginx/ssl:ro' docker-compose.prod.yml
fi

echo -e "${GREEN}✓ Configuration updated${NC}"

# Restart nginx with SSL
echo ""
echo -e "${BLUE}Starting Nginx with SSL...${NC}"
docker compose -f docker-compose.prod.yml up -d nginx
sleep 5

# Verify nginx configuration
if docker compose -f docker-compose.prod.yml exec -T nginx nginx -t > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}Error: Nginx configuration is invalid!${NC}"
    docker compose -f docker-compose.prod.yml exec -T nginx nginx -t
    exit 1
fi

# Verify nginx is running
if docker compose -f docker-compose.prod.yml ps nginx | grep -q "Up"; then
    echo -e "${GREEN}✓ Nginx started successfully${NC}"
else
    echo -e "${RED}Error: Nginx failed to start${NC}"
    docker compose -f docker-compose.prod.yml logs nginx | tail -20
    exit 1
fi

# Setup auto-renewal
echo ""
echo -e "${BLUE}Setting up certificate auto-renewal...${NC}"
# Create renewal script
cat > /etc/cron.monthly/renew-ssl-cert <<EOF
#!/bin/bash
certbot renew --quiet --deploy-hook "cd $APP_DIR && cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/$DOMAIN/fullchain.pem && cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/$DOMAIN/privkey.pem && cp /etc/letsencrypt/live/$DOMAIN/chain.pem nginx/ssl/$DOMAIN/chain.pem && docker compose -f docker-compose.prod.yml restart nginx"
EOF
chmod +x /etc/cron.monthly/renew-ssl-cert
echo -e "${GREEN}✓ Auto-renewal configured${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "✅ SSL Setup Complete!"
echo "=========================================="
echo "${NC}"

echo -e "${BLUE}Certificate Details:${NC}"
certbot certificates

echo ""
echo -e "${GREEN}Your site is now available at: https://$DOMAIN${NC}"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "  - Certificates will auto-renew monthly"
echo "  - Update your .env file:"
echo "    ${BLUE}SECURE_SSL_REDIRECT=1${NC}"
echo "    ${BLUE}SESSION_COOKIE_SECURE=1${NC}"
echo "    ${BLUE}CSRF_COOKIE_SECURE=1${NC}"
echo ""
echo -e "${GREEN}SSL setup complete! 🎉${NC}"
echo ""

