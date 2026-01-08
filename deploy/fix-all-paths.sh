#!/bin/bash

# Script to replace all /opt/travel-marketplace-backend references
# with dynamic path detection

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Fixing all hardcoded /opt/travel-marketplace-backend paths..."
echo "Project directory: $PROJECT_DIR"
echo ""

# Find all files with /opt/travel-marketplace-backend and replace
find "$SCRIPT_DIR" -type f \( -name "*.sh" -o -name "*.md" \) -exec sed -i.bak \
    's|/opt/travel-marketplace-backend|'"$PROJECT_DIR"'|g' {} \;

echo "✓ Fixed all hardcoded paths"
echo ""
echo "Backup files created with .bak extension"
echo "To remove backups: find $SCRIPT_DIR -name '*.bak' -delete"
echo ""

