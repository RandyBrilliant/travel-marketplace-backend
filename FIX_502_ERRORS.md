# Fix for Intermittent 502 Bad Gateway Errors

## Problem

Intermittent 502 Bad Gateway errors that resolve on refresh. This typically happens when:
- Nginx can't connect to the API container (temporary unavailability)
- API container is restarting (memory pressure, health checks)
- Request timeouts
- Database connection issues

## Root Causes on 2GB Server

1. **No upstream retry logic** - Nginx immediately returns 502 if API is temporarily unavailable
2. **No connection keepalive** - Each request creates new connection (slower, more failures)
3. **Container restarts** - Memory pressure causes containers to restart
4. **Timeout mismatches** - Different timeouts between nginx and gunicorn

## Fixes Applied

### 1. Upstream Configuration with Retries ✅

Added upstream block with:
- **max_fails=3** - Mark server as down after 3 failures
- **fail_timeout=30s** - Retry after 30 seconds
- **keepalive connections** - Reuse connections (faster, more reliable)

### 2. Retry Logic ✅

Added `proxy_next_upstream` to retry on:
- Connection errors
- Timeouts
- HTTP 502, 503, 504 errors

**Retry up to 2 times** before giving up.

### 3. Connection Keepalive ✅

- **keepalive 32** - Maintain 32 idle connections
- **keepalive_timeout 60s** - Keep connections alive for 60s
- **keepalive_requests 100** - Reuse connection for up to 100 requests

This reduces connection overhead and improves reliability.

### 4. Optimized Timeouts ✅

- **proxy_connect_timeout: 10s** - Fast connection timeout
- **proxy_send_timeout: 90s** - Allow longer requests
- **proxy_read_timeout: 90s** - Match gunicorn timeout (120s)

### 5. Better Error Handling ✅

- Retry on temporary errors (502, 503, 504)
- Don't retry on client errors (400, 401, 403, 404)
- Fast failover to prevent long waits

## How It Works Now

**Before:**
```
Request → Nginx → API (unavailable) → 502 Error ❌
```

**After:**
```
Request → Nginx → API (unavailable) → Retry → API (available) → 200 OK ✅
```

## Deployment

After updating the nginx config:

```bash
# On your server
cd /opt/travel-marketplace-backend

# Restart nginx to apply changes
docker compose -f docker-compose.prod.yml restart nginx

# Or if you've updated the file in git:
git pull
sudo ./deploy/deploy.sh
```

## Monitoring

Check nginx error logs for upstream issues:

```bash
# View nginx error logs
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml logs nginx | grep -i "upstream\|502\|503\|504"

# Check API container health
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml ps api

# Monitor memory usage (502s often caused by OOM)
docker stats --no-stream
```

## Expected Results

✅ **Fewer 502 errors** - Retries handle temporary failures  
✅ **Faster responses** - Keepalive connections reduce latency  
✅ **Better reliability** - Automatic retry on transient errors  
✅ **Graceful degradation** - Fast failover instead of hanging

## Additional Recommendations

### If 502s persist:

1. **Check container restarts:**
   ```bash
   docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml ps
   # Look for containers with high restart counts
   ```

2. **Monitor memory:**
   ```bash
   docker stats
   # If containers are hitting memory limits, consider upgrading to 4GB
   ```

3. **Check database connections:**
   ```bash
   docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml exec db psql -U your_user -d your_db -c "SELECT count(*) FROM pg_stat_activity;"
   ```

4. **Review logs:**
   ```bash
   docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml logs api --tail=100 | grep -i error
   ```

### Long-term Solutions

- **Upgrade to 4GB RAM** - More headroom prevents container restarts
- **Add monitoring** - Alert on 502 errors to catch issues early
- **Database connection pooling** - Use PgBouncer for better connection management
- **Load balancing** - Multiple API instances for redundancy

## Technical Details

### Upstream Block
```nginx
upstream api_backend {
    server api:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
    keepalive_timeout 60s;
    keepalive_requests 100;
}
```

### Retry Configuration
```nginx
proxy_next_upstream error timeout http_502 http_503 http_504;
proxy_next_upstream_tries 2;
proxy_next_upstream_timeout 5s;
```

This means:
- Retry on connection errors, timeouts, and 502/503/504
- Try up to 2 times (original + 1 retry)
- Total timeout for retries: 5 seconds

## Summary

The fixes add **resilience** to handle temporary failures:
- ✅ Automatic retries
- ✅ Connection reuse
- ✅ Better timeout handling
- ✅ Graceful error recovery

502 errors should now be **rare** and **self-healing** when they do occur.

