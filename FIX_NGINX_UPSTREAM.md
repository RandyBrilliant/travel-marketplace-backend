# Nginx Upstream Configuration Fix

## Problem

Nginx container was crashing with error:
```
nginx: [emerg] "upstream" directive is not allowed here in /etc/nginx/conf.d/api.goholiday.id.conf:59
```

## Root Cause

The `upstream api_backend` block was placed inside a `server` block. In nginx configuration, `upstream` directives must be at the **top level** (in the `http` context), not inside `server` blocks.

## Solution

Moved the `upstream api_backend` block to the top of the configuration file, before any `server` blocks.

### Before (INCORRECT)
```nginx
server {
    listen 443 ssl;
    server_name api.goholiday.id;
    
    # This is WRONG - upstream inside server block
    upstream api_backend {
        server api:8000;
    }
    
    location / {
        proxy_pass http://api_backend;
    }
}
```

### After (CORRECT)
```nginx
# Upstream at top level - CORRECT
upstream api_backend {
    server api:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
    keepalive_timeout 60s;
    keepalive_requests 100;
}

server {
    listen 443 ssl;
    server_name api.goholiday.id;
    
    location / {
        proxy_pass http://api_backend;
    }
}
```

## How to Deploy the Fix

**On your server:**

```bash
cd /opt/travel-marketplace-backend
git pull
docker compose -f docker-compose.prod.yml restart nginx
```

Or run the full deployment:

```bash
sudo ./deploy/deploy.sh
```

## Verification

After deploying, check that nginx is running:

```bash
docker compose -f docker-compose.prod.yml ps nginx
```

You should see nginx status as `Up` (healthy), not `Restarting`.

Check nginx logs:

```bash
docker compose -f docker-compose.prod.yml logs nginx --tail=20
```

You should see:
```
/docker-entrypoint.sh: Configuration complete; ready for start up
```

Without the `[emerg]` error.

## Related Fixes

This fix is part of the 502 Bad Gateway resolution, which includes:
- Upstream with keepalive connections
- Retry logic for failed requests
- Connection pooling for better performance

See `FIX_502_ERRORS.md` for more details.

