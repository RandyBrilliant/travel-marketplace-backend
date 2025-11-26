#!/bin/sh

set -euo pipefail

python manage.py collectstatic --noinput --verbosity 0 || true
python manage.py migrate --noinput

exec "$@"

