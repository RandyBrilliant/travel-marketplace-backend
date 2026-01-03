#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

APP_DIR="${APP_DIR:-/opt/travel-marketplace-backend}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

echo "=========================================="
echo "Travel Marketplace Backend - Backup"
echo "=========================================="

# Create backup directory
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup-$TIMESTAMP"
mkdir -p "$BACKUP_PATH"

cd "$APP_DIR"

# Check if containers are running
if ! docker compose -f docker-compose.prod.yml ps db | grep -q "Up"; then
    echo -e "${RED}Error: Database container is not running${NC}"
    exit 1
fi

# Get database credentials from .env
if [ -f .env ]; then
    source .env
fi

DB_USER="${SQL_USER:-travel_user}"
DB_NAME="${SQL_DATABASE:-travel_marketplace}"
DB_CONTAINER="dcnetwork-api-db"

# Backup database
echo -e "${GREEN}[1/3] Backing up database...${NC}"
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_PATH/database.sql.gz"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Database backup completed${NC}"
else
    echo -e "${RED}Database backup failed${NC}"
    exit 1
fi

# Backup media files
echo -e "${GREEN}[2/3] Backing up media files...${NC}"
if [ -d "$APP_DIR/media" ] && [ "$(ls -A $APP_DIR/media 2>/dev/null)" ]; then
    tar -czf "$BACKUP_PATH/media.tar.gz" -C "$APP_DIR" media/
    echo -e "${GREEN}Media backup completed${NC}"
else
    echo -e "${YELLOW}No media files to backup${NC}"
fi

# Backup environment file (without sensitive data)
echo -e "${GREEN}[3/3] Backing up configuration...${NC}"
if [ -f .env ]; then
    # Create a sanitized version
    grep -v -E "^(SECRET_KEY|SQL_PASSWORD|MAILGUN_SMTP_PASSWORD|CELERY_BROKER_URL|CELERY_RESULT_BACKEND)=" .env > "$BACKUP_PATH/env.sanitized" 2>/dev/null || true
    echo -e "${GREEN}Configuration backup completed${NC}"
fi

# Create backup info file
cat > "$BACKUP_PATH/backup-info.txt" << EOF
Backup Date: $(date)
Database: $DB_NAME
Database User: $DB_USER
Backup Size: $(du -sh "$BACKUP_PATH" | cut -f1)
EOF

# Compress entire backup
echo -e "${GREEN}Compressing backup...${NC}"
cd "$BACKUP_DIR"
tar -czf "backup-$TIMESTAMP.tar.gz" "backup-$TIMESTAMP"
rm -rf "backup-$TIMESTAMP"
FINAL_BACKUP="backup-$TIMESTAMP.tar.gz"

BACKUP_SIZE=$(du -h "$BACKUP_DIR/$FINAL_BACKUP" | cut -f1)

echo ""
echo -e "${GREEN}=========================================="
echo "Backup completed successfully!"
echo "==========================================${NC}"
echo ""
echo "Backup file: $BACKUP_DIR/$FINAL_BACKUP"
echo "Backup size: $BACKUP_SIZE"
echo ""

# Cleanup old backups
echo -e "${GREEN}Cleaning up old backups (older than $RETENTION_DAYS days)...${NC}"
find "$BACKUP_DIR" -name "backup-*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete
echo -e "${GREEN}Cleanup completed${NC}"

# List remaining backups
echo ""
echo "Remaining backups:"
ls -lh "$BACKUP_DIR"/backup-*.tar.gz 2>/dev/null | tail -5 || echo "No backups found"
echo ""

