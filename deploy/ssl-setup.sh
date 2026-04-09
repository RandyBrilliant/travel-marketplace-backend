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

# Create directory for certbot webroot (nginx serves this over HTTP for ACME challenge)
echo ""
echo -e "${BLUE}[4/6] Preparing webroot directory and ensuring nginx has the volume mount...${NC}"
mkdir -p /var/www/certbot

CERTBOT_MOUNT="/var/www/certbot:/var/www/certbot:ro"

# Add the certbot volume to docker-compose.prod.yml if not already present
if ! grep -qF "$CERTBOT_MOUNT" docker-compose.prod.yml; then
    echo -e "${YELLOW}  → Adding /var/www/certbot volume mount to nginx in docker-compose.prod.yml...${NC}"
    # Insert the mount line right after the nginx ssl volume line
    sed -i "s|      - ./nginx/ssl:/etc/nginx/ssl:ro|      - ./nginx/ssl:/etc/nginx/ssl:ro\n      - /var/www/certbot:/var/www/certbot:ro|" docker-compose.prod.yml
    echo -e "${GREEN}  ✓ Volume mount added${NC}"
else
    echo -e "${GREEN}  ✓ Volume mount already present${NC}"
fi

# Force-recreate nginx so the new volume mount takes effect
echo -e "${YELLOW}  → Recreating nginx container to apply volume changes...${NC}"
docker compose -f docker-compose.prod.yml up -d --force-recreate nginx
sleep 4

# Confirm nginx came back up
if ! docker compose -f docker-compose.prod.yml ps nginx | grep -q "Up"; then
    echo -e "${RED}Error: Nginx failed to start after recreate.${NC}"
    docker compose -f docker-compose.prod.yml logs nginx | tail -20
    exit 1
fi

# Verify the challenge path is actually reachable before calling certbot
echo -e "${YELLOW}  → Testing ACME challenge path...${NC}"
TESTFILE="/var/www/certbot/.well-known/acme-challenge/.test-$(date +%s)"
mkdir -p "$(dirname "$TESTFILE")"
echo "ok" > "$TESTFILE"
HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" \
    "http://$DOMAIN/.well-known/acme-challenge/$(basename "$TESTFILE")" 2>/dev/null || true)
rm -f "$TESTFILE"

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}  ✓ Challenge path is reachable (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}Error: Challenge path returned HTTP $HTTP_CODE (expected 200).${NC}"
    echo "  This means nginx is NOT serving /var/www/certbot correctly."
    echo "  Check:"
    echo "    1. docker compose -f docker-compose.prod.yml exec nginx cat /etc/nginx/conf.d/data.goholiday.id.conf"
    echo "       Must have: location /.well-known/acme-challenge/ { root /var/www/certbot; }"
    echo "    2. docker compose -f docker-compose.prod.yml exec nginx ls /var/www/certbot/.well-known/acme-challenge/"
    echo "       Must list files (if empty, the volume mount still isn't working)"
    exit 1
fi

echo -e "${GREEN}✓ Webroot ready at /var/www/certbot${NC}"

# Generate certificate using webroot (nginx stays up, no port conflict)
echo ""
echo -e "${BLUE}[5/6] Generating SSL certificate (webroot method)...${NC}"
certbot certonly \
    --webroot \
    -w /var/www/certbot \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive \
    --keep-until-expiring || {
    echo -e "${RED}Error: Certificate generation failed${NC}"
    echo "Common issues:"
    echo "  - DNS not pointing to this server"
    echo "  - Port 80 not accessible from the internet"
    echo "  - /var/www/certbot not mounted into the nginx container"
    echo "    (check docker-compose.prod.yml nginx volumes)"
    echo "  - Too many certificate requests (Let's Encrypt rate limit)"
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

# Remove old broken monthly cron if it exists
rm -f /etc/cron.monthly/renew-ssl-cert

# Create a dedicated renewal script that uses webroot (nginx stays up)
cat > /usr/local/bin/renew-ssl-cert.sh <<RENEWSCRIPT
#!/bin/bash
# Let's Encrypt auto-renewal for $DOMAIN
# Uses webroot authenticator so nginx stays running during renewal.
# Runs twice daily via cron; certbot only renews when <30 days remain.

set -euo pipefail

APP_DIR="$APP_DIR"
DOMAIN="$DOMAIN"

certbot renew \\
    --webroot -w /var/www/certbot \\
    --cert-name "\$DOMAIN" \\
    --deploy-hook "
        set -e
        cp /etc/letsencrypt/live/\$DOMAIN/fullchain.pem \$APP_DIR/nginx/ssl/\$DOMAIN/fullchain.pem
        cp /etc/letsencrypt/live/\$DOMAIN/privkey.pem  \$APP_DIR/nginx/ssl/\$DOMAIN/privkey.pem
        cp /etc/letsencrypt/live/\$DOMAIN/chain.pem    \$APP_DIR/nginx/ssl/\$DOMAIN/chain.pem
        chmod 644 \$APP_DIR/nginx/ssl/\$DOMAIN/fullchain.pem \$APP_DIR/nginx/ssl/\$DOMAIN/chain.pem
        chmod 600 \$APP_DIR/nginx/ssl/\$DOMAIN/privkey.pem
        docker compose -f \$APP_DIR/docker-compose.prod.yml exec -T nginx nginx -s reload
    "
RENEWSCRIPT
chmod +x /usr/local/bin/renew-ssl-cert.sh

# Install twice-daily cron (standard Let's Encrypt recommendation)
# Runs at 03:17 and 15:17 with jitter to reduce Let's Encrypt server load.
CRON_LINE="17 3,15 * * * root /usr/local/bin/renew-ssl-cert.sh >> /var/log/certbot-renew.log 2>&1"
CRON_FILE="/etc/cron.d/certbot-renew"
echo "$CRON_LINE" > "$CRON_FILE"
chmod 644 "$CRON_FILE"
echo -e "${GREEN}✓ Auto-renewal configured (twice daily, logs: /var/log/certbot-renew.log)${NC}"

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
echo "  - Certificates will auto-renew twice daily (03:17 and 15:17)"
echo "  - Renewal logs: /var/log/certbot-renew.log"
echo "  - Test renewal dry-run: sudo certbot renew --dry-run --webroot -w /var/www/certbot"
echo "  - Update your .env file:"
echo "    ${BLUE}SECURE_SSL_REDIRECT=1${NC}"
echo "    ${BLUE}SESSION_COOKIE_SECURE=1${NC}"
echo "    ${BLUE}CSRF_COOKIE_SECURE=1${NC}"
echo ""
echo -e "${GREEN}SSL setup complete! 🎉${NC}"
echo ""

