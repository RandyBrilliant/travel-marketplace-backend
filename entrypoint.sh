#!/bin/sh

set -euo pipefail

# Create media directories if they don't exist (needed for volume mounts)
# Note: If volume mount has permission issues, create these directories on the host
# with: mkdir -p media/profile_photos/{staff,supplier,reseller} && chmod -R 777 media
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

