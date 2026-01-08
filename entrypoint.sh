#!/bin/sh

set -euo pipefail

# Create logs directory (required for Django logging)
mkdir -p /app/logs
chmod 755 /app/logs

# Create media directories if they don't exist (needed for volume mounts)
# Handle case where file exists instead of directory
if [ -f /app/media/profile_photos ]; then
    rm -f /app/media/profile_photos
fi
mkdir -p /app/media/profile_photos/staff /app/media/profile_photos/supplier /app/media/profile_photos/reseller 2>/dev/null || true

# Production checks
if [ "${DEBUG:-0}" = "0" ]; then
    # Verify SECRET_KEY is set in production
    if [ -z "${SECRET_KEY:-}" ] || [ "${SECRET_KEY}" = "change-me" ] || [ "${SECRET_KEY}" = "change-me-to-secure-random-key" ]; then
        echo "ERROR: SECRET_KEY must be set to a secure value in production!"
        exit 1
    fi
    
    # Verify ALLOWED_HOSTS includes the domain
    if [ -z "${ALLOWED_HOSTS:-}" ]; then
        echo "WARNING: ALLOWED_HOSTS is not set in production!"
    fi
fi

# Run migrations first
python manage.py migrate --noinput

exec "$@"

