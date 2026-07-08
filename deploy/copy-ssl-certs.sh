#!/bin/bash
# Copy Let's Encrypt certs into nginx/ssl/ and reload Docker nginx.
# Run after: certbot certonly / certbot renew (when not using ssl-setup.sh deploy-hook).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(dirname "$SCRIPT_DIR")}"
DOMAIN="${SSL_DOMAIN:-data.goholiday.id}"

if [ "$EUID" -ne 0 ]; then
    echo "Run with sudo: sudo $0"
    exit 1
fi

LE_DIR="/etc/letsencrypt/live/$DOMAIN"
NGINX_SSL_DIR="$APP_DIR/nginx/ssl/$DOMAIN"

for f in fullchain.pem privkey.pem chain.pem; do
    if [ ! -f "$LE_DIR/$f" ]; then
        echo "Missing $LE_DIR/$f — run certbot first."
        exit 1
    fi
done

mkdir -p "$NGINX_SSL_DIR"
cp "$LE_DIR/fullchain.pem" "$NGINX_SSL_DIR/fullchain.pem"
cp "$LE_DIR/privkey.pem" "$NGINX_SSL_DIR/privkey.pem"
cp "$LE_DIR/chain.pem" "$NGINX_SSL_DIR/chain.pem"
chmod 644 "$NGINX_SSL_DIR/fullchain.pem" "$NGINX_SSL_DIR/chain.pem"
chmod 600 "$NGINX_SSL_DIR/privkey.pem"

cd "$APP_DIR"
docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload

echo "Copied certs and reloaded nginx."
openssl x509 -in "$NGINX_SSL_DIR/fullchain.pem" -noout -dates -subject
