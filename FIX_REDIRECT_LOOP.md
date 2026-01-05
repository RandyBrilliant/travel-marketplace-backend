# Fix "Too Many Redirects" Error

## Problem

Infinite redirect loop causing "ERR_TOO_MANY_REDIRECTS" error.

## Root Cause

Django's `SECURE_SSL_REDIRECT=True` conflicts with nginx's HTTP→HTTPS redirect, creating a loop:

1. User requests HTTP → Nginx redirects to HTTPS ✅
2. Django sees request and redirects again → Loop ❌

## Quick Fix

**On your server, check and fix the `.env` file:**

```bash
cd /opt/travel-marketplace-backend

# Check current setting
grep SECURE_SSL_REDIRECT .env

# It should show: SECURE_SSL_REDIRECT=false
# If it shows: SECURE_SSL_REDIRECT=true, fix it:

# Fix the redirect setting
sudo sed -i 's/SECURE_SSL_REDIRECT=true/SECURE_SSL_REDIRECT=false/' .env

# Or manually edit:
sudo nano .env
# Find SECURE_SSL_REDIRECT and set it to: false
```

**Restart the API container:**

```bash
docker compose -f docker-compose.prod.yml restart api
```

## Why This Happens

- **Nginx** handles HTTP→HTTPS redirect (port 80 → 443)
- **Django** should NOT redirect when behind nginx
- Both redirecting = infinite loop

## Solution Applied

1. ✅ Added `SECURE_PROXY_SSL_HEADER` to Django settings
   - Tells Django to trust nginx's `X-Forwarded-Proto` header
   - Django knows it's receiving HTTPS requests

2. ✅ Ensure `SECURE_SSL_REDIRECT=false` in `.env`
   - Prevents Django from redirecting
   - Nginx handles all redirects

## Verify Fix

After restarting:

```bash
# Test HTTP (should redirect to HTTPS once)
curl -I http://api.goholiday.id/health/

# Test HTTPS (should work, no redirect)
curl -I https://api.goholiday.id/health/
```

## Expected Behavior

**HTTP Request:**
```
http://api.goholiday.id → 301 Redirect → https://api.goholiday.id ✅
```

**HTTPS Request:**
```
https://api.goholiday.id → 200 OK ✅
```

No more loops!

## If Problem Persists

1. **Check nginx logs:**
   ```bash
   docker compose -f docker-compose.prod.yml logs nginx | grep redirect
   ```

2. **Check Django logs:**
   ```bash
   docker compose -f docker-compose.prod.yml logs api | grep -i redirect
   ```

3. **Verify .env file:**
   ```bash
   cat /opt/travel-marketplace-backend/.env | grep SSL
   ```

4. **Clear browser cache** - Old redirects might be cached

## Summary

- ✅ Set `SECURE_SSL_REDIRECT=false` in `.env`
- ✅ Django now trusts nginx proxy headers
- ✅ Only nginx handles redirects (no conflict)
- ✅ Restart API container to apply changes

