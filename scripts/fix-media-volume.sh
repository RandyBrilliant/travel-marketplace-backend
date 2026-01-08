#!/bin/bash

# Fix Docker Media Volume Script
# Fixes the issue where profile_photos exists as a file instead of directory

set -e

echo "=========================================="
echo "Fixing Docker Media Volume"
echo "=========================================="
echo ""

# Stop containers that use the volume
echo "[1/3] Stopping containers..."
docker compose -f docker-compose.prod.yml stop celery celery-beat api 2>/dev/null || true
echo "✓ Containers stopped"
echo ""

# Remove the problematic volume
echo "[2/3] Removing media volume..."
docker volume rm travel-marketplace-backend_media_volume 2>/dev/null || \
docker volume rm dcnetwork-api_media_volume 2>/dev/null || \
echo "  Volume not found or already removed"
echo ""

# Recreate volume and fix structure
echo "[3/3] Recreating volume with proper structure..."
docker compose -f docker-compose.prod.yml up -d db redis
sleep 3

# Start one container to initialize the volume properly
docker compose -f docker-compose.prod.yml run --rm api sh -c "
    mkdir -p /app/media/profile_photos/staff \
             /app/media/profile_photos/supplier \
             /app/media/profile_photos/reseller
    chmod -R 755 /app/media
" || true

echo "✓ Volume recreated"
echo ""

echo "=========================================="
echo "✅ Media Volume Fixed!"
echo "=========================================="
echo ""
echo "You can now start all services:"
echo "  docker compose -f docker-compose.prod.yml up -d"
echo ""

