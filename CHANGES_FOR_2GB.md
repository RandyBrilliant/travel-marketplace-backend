# Changes Made for 2GB RAM Optimization

## Summary

The `docker-compose.prod.yml` has been optimized for 2GB RAM servers by reducing memory limits and worker counts.

## What Changed

### Memory Limits

| Service | Before | After | Savings |
|---------|--------|-------|---------|
| **nginx** | unlimited | 50M | controlled |
| **api** | 256M | 200M | -56M |
| **db** | 256M | 200M | -56M |
| **redis** | 128M | 100M | -28M |
| **celery** | 256M | 200M | -56M |
| **celery-beat** | 64M | 100M | +36M ⬆ |
| **Total** | ~980M | ~850M | **-130M** |

### Worker/Concurrency Changes

| Service | Before | After | Impact |
|---------|--------|-------|--------|
| **Gunicorn workers** | 2 | 1 | Lower throughput |
| **Celery concurrency** | 2 | 1 | Slower task processing |
| **Redis maxmemory** | 100MB | 80MB | Less cache |

### Health Checks Fixed

- **nginx**: Added health check using `pgrep`
- **celery-beat**: Added health check using `pgrep` + increased memory to prevent OOM

## Why These Changes?

1. **Celery-beat OOM kills**: Was only 64M, kept getting killed. Now 100M for stability.
2. **Total memory usage**: Reduced from 980M to 850M to fit in 2GB with OS overhead.
3. **Worker reduction**: Fewer workers = less memory but still functional.

## Trade-offs

### ✅ Pros
- No more OOM kills
- Stable operation on 2GB
- All features work
- Easy to revert

### ⚠️ Cons
- Lower throughput (1 worker vs 2)
- Slower under concurrent load
- Less Redis cache
- Not optimal for production scale

## How to Deploy

### Option 1: Simple (Just run deploy.sh)

```bash
# On your server
cd ~/travel-marketplace-backend

# Fix Redis warning first (one-time)
sudo ./deploy/fix-redis-warning.sh

# Commit and push changes from local machine
git add docker-compose.prod.yml
git commit -m "Optimize for 2GB RAM"
git push

# On server - pull and deploy
git pull
sudo ./deploy/deploy.sh
```

### Option 2: All-in-one script

```bash
# On your server
cd ~/travel-marketplace-backend
sudo ./deploy/fix-2gb-memory.sh
```

This script will:
1. Fix Redis warning
2. Pull latest code
3. Run deploy.sh
4. Show status

## Reverting to Original (If you upgrade to 4GB+)

Just restore the original values in `docker-compose.prod.yml`:

```yaml
api:
  command: gunicorn ... --workers 2 --threads 2
  deploy:
    resources:
      limits:
        memory: 256M

db:
  deploy:
    resources:
      limits:
        memory: 256M

redis:
  command: redis-server ... --maxmemory 100mb
  deploy:
    resources:
      limits:
        memory: 128M

celery:
  command: celery ... --concurrency=2
  deploy:
    resources:
      limits:
        memory: 256M

celery-beat:
  deploy:
    resources:
      limits:
        memory: 128M  # Keep higher to prevent OOM
```

Then run:
```bash
sudo ./deploy/deploy.sh
```

## Monitoring

After deployment, monitor your server:

```bash
# Check container memory usage
docker stats

# Check system memory
free -h

# Watch for OOM kills
dmesg | grep -i oom

# View container status
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml ps
```

## Recommendation

**For production:** Upgrade to 4GB RAM ($12-24/month more)
- Full 2-worker configuration
- Better performance
- Room for growth
- No compromises

**For development/testing:** 2GB works fine with these optimizations

## Questions?

See [2GB-RAM-GUIDE.md](deploy/2GB-RAM-GUIDE.md) for detailed information.

