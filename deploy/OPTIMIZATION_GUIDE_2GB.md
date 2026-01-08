# Complete Optimization Guide for 2GB RAM + 1vCPU Server

This guide provides comprehensive optimization strategies for running the Travel Marketplace API on a Digital Ocean droplet with 2GB RAM and 1 vCPU.

## Table of Contents
- [Quick Start](#quick-start)
- [System Requirements](#system-requirements)
- [Optimization Strategy](#optimization-strategy)
- [Configuration Details](#configuration-details)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Upgrade Path](#upgrade-path)

---

## Quick Start

### 1. Run the Optimization Script

```bash
cd /path/to/travel-marketplace-backend
sudo ./deploy/optimize-2gb.sh
```

This script will:
- Configure system memory settings
- Set up 2GB swap space
- Optimize Docker daemon
- Create PostgreSQL configuration
- Optimize Nginx settings
- Configure log rotation

### 2. Deploy the Application

```bash
sudo ./deploy/deploy.sh
```

### 3. Monitor Resources

```bash
# Real-time container stats
docker stats

# System memory
free -h

# Detailed monitoring
htop
```

---

## System Requirements

### Minimum Specifications
- **RAM**: 2GB
- **vCPU**: 1 core
- **Storage**: 25GB SSD
- **Network**: 1000 Mbps

### Recommended Upgrades
For production environments with moderate traffic:
- **RAM**: 4GB (better performance and stability)
- **vCPU**: 2 cores (better concurrency)
- **Storage**: 50GB SSD

---

## Optimization Strategy

### Memory Allocation Plan

```
Total System Memory: 2GB (2048MB)
├── Docker Containers: ~850MB
│   ├── API (Gunicorn):      200MB (1 worker, 2 threads)
│   ├── PostgreSQL:          200MB (optimized settings)
│   ├── Redis:               100MB (80MB max data)
│   ├── Celery Worker:       200MB (1 concurrent task)
│   ├── Celery Beat:         100MB
│   └── Nginx:                50MB
├── System Overhead:         ~300MB
│   ├── Kernel:              ~150MB
│   ├── Docker daemon:       ~100MB
│   └── SSH/System:           ~50MB
├── Available Buffer:        ~900MB
└── Swap Space:             2048MB (emergency overflow)
```

### CPU Allocation Plan

```
Single vCPU (1 core)
├── Nginx:           10% (I/O bound, efficient)
├── Gunicorn:        40% (1 worker handles most API requests)
├── PostgreSQL:      20% (optimized queries)
├── Redis:            5% (very efficient)
├── Celery:          20% (background tasks)
├── System:           5%
```

---

## Configuration Details

### 1. Docker Compose Settings

Your `docker-compose.prod.yml` already has optimized settings:

```yaml
# API Service
api:
  command: gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 2 --timeout 120
  deploy:
    resources:
      limits:
        cpus: '0.4'
        memory: 200M
      reservations:
        cpus: '0.2'
        memory: 100M

# Database
db:
  deploy:
    resources:
      limits:
        cpus: '0.3'
        memory: 200M
      reservations:
        cpus: '0.1'
        memory: 64M

# Redis
redis:
  command: redis-server --appendonly yes --maxmemory 80mb --maxmemory-policy allkeys-lru
  deploy:
    resources:
      limits:
        cpus: '0.15'
        memory: 100M

# Celery Worker
celery:
  command: celery -A backend worker --loglevel=info --concurrency=1 --max-tasks-per-child=1000
  deploy:
    resources:
      limits:
        cpus: '0.4'
        memory: 200M
```

### 2. System Settings

#### Memory Overcommit (for Redis)
```bash
# Add to /etc/sysctl.conf
vm.overcommit_memory = 1
vm.swappiness = 10
```

#### Swap Configuration
```bash
# Create 2GB swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. PostgreSQL Optimization

Create `postgres/postgresql.conf`:

```conf
# Memory Configuration (for ~200MB container limit)
shared_buffers = 64MB              # 25% of container memory
effective_cache_size = 128MB       
work_mem = 2MB                     # Per operation
maintenance_work_mem = 16MB        

# Connection Settings
max_connections = 50               # Reduced for low memory
superuser_reserved_connections = 3

# Write-Ahead Log
wal_buffers = 2MB
min_wal_size = 80MB
max_wal_size = 256MB

# Query Planning (SSD optimized)
random_page_cost = 1.1
effective_io_concurrency = 200

# Checkpoints
checkpoint_completion_target = 0.9
```

Mount in docker-compose:
```yaml
db:
  volumes:
    - ./postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
  command: postgres -c 'config_file=/etc/postgresql/postgresql.conf'
```

### 4. Nginx Optimization

Key settings for low-resource environment:

```nginx
worker_processes 1;  # Match single vCPU
worker_rlimit_nofile 8192;

events {
    worker_connections 1024;  # Reduced from 2048
    use epoll;
    multi_accept on;
}

http {
    keepalive_timeout 30;  # Reduced from 65
    keepalive_requests 100;
    
    # Smaller buffers
    client_body_buffer_size 128k;
    client_max_body_size 20M;
    
    # Efficient gzip
    gzip on;
    gzip_comp_level 6;
    gzip_min_length 256;
}
```

### 5. Django Settings

Optimization in `.env`:

```bash
# Database
DB_CONN_MAX_AGE=300              # Connection pooling (5 min)

# JWT Tokens
ACCESS_TOKEN_LIFETIME_MINUTES=15  # Shorter = less cache
REFRESH_TOKEN_LIFETIME_DAYS=7     # Reasonable refresh

# Debug (MUST be off in production)
DEBUG=0
```

In `settings.py` (already configured):

```python
# Celery - conservative limits
CELERY_TASK_TIME_LIMIT = 30 * 60        # 30 minutes max
CELERY_TASK_SOFT_TIME_LIMIT = 60        # 1 minute soft limit
CELERY_WORKER_PREFETCH_MULTIPLIER = 1   # Don't prefetch tasks
CELERY_TASK_ACKS_LATE = True            # Ack after completion

# Cache - Redis with compression
CACHES = {
    'default': {
        'OPTIONS': {
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,  # Don't fail if Redis down
        }
    }
}
```

### 6. Docker Daemon

Create/update `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

---

## Monitoring

### Real-Time Monitoring

```bash
# Container resource usage
docker stats

# System memory
free -h
watch -n 1 free -h

# Detailed system monitor
htop

# Container logs
docker compose -f docker-compose.prod.yml logs -f

# Specific service logs
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f db
```

### Key Metrics to Watch

1. **Memory Usage**
   - Keep total under 1.8GB (leave buffer)
   - Watch for swap usage (should be minimal)
   - Alert if swap > 500MB

2. **CPU Usage**
   - API should stay under 50%
   - Database under 30%
   - Alert if sustained > 80%

3. **Disk I/O**
   - PostgreSQL should have low wait times
   - Monitor with `iostat -x 1`

4. **Response Times**
   - API health endpoint: < 200ms
   - Database queries: < 100ms average

### Setting Up Monitoring (Optional)

#### Netdata (Lightweight)
```bash
bash <(curl -Ss https://my-netdata.io/kickstart.sh)
```

#### Simple Alert Script
```bash
# Create /opt/monitor.sh
#!/bin/bash
MEM_USAGE=$(free | grep Mem | awk '{print ($3/$2) * 100.0}')
if (( $(echo "$MEM_USAGE > 85" | bc -l) )); then
    echo "High memory usage: $MEM_USAGE%" | mail -s "Server Alert" admin@yourdomain.com
fi

# Add to crontab
*/5 * * * * /opt/monitor.sh
```

---

## Troubleshooting

### Common Issues

#### 1. Out of Memory (OOM) Errors

**Symptoms:**
- Container randomly restarts
- `docker logs` shows "Killed"
- System becomes unresponsive

**Solutions:**
```bash
# Check memory usage
docker stats

# Restart specific service
docker compose -f docker-compose.prod.yml restart api

# Check swap usage
free -h

# If swap not active
sudo swapon /swapfile

# Reduce worker processes temporarily
# Edit docker-compose.prod.yml
command: gunicorn ... --workers 1 --threads 1
```

#### 2. Slow Response Times

**Symptoms:**
- API requests take > 2 seconds
- High CPU usage

**Solutions:**
```bash
# Check slow queries
docker compose -f docker-compose.prod.yml exec db psql -U $SQL_USER -d $SQL_DATABASE -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Restart services
docker compose -f docker-compose.prod.yml restart

# Check for background tasks
docker compose -f docker-compose.prod.yml exec api python manage.py shell
>>> from celery import current_app
>>> inspect = current_app.control.inspect()
>>> print(inspect.active())
```

#### 3. Database Connection Errors

**Symptoms:**
- "Too many connections"
- Connection timeouts

**Solutions:**
```bash
# Check current connections
docker compose -f docker-compose.prod.yml exec db psql -U $SQL_USER -d $SQL_DATABASE -c "SELECT count(*) FROM pg_stat_activity;"

# Reduce max_connections in PostgreSQL
# Edit postgres/postgresql.conf
max_connections = 30

# Restart database
docker compose -f docker-compose.prod.yml restart db
```

#### 4. Redis Memory Issues

**Symptoms:**
- Redis memory limit reached
- Cache errors in logs

**Solutions:**
```bash
# Check Redis memory
docker compose -f docker-compose.prod.yml exec redis redis-cli INFO memory

# Flush cache if needed (WARNING: clears all cache)
docker compose -f docker-compose.prod.yml exec redis redis-cli FLUSHALL

# Reduce Redis max memory
# Edit docker-compose.prod.yml
command: redis-server --maxmemory 64mb --maxmemory-policy allkeys-lru
```

#### 5. Disk Space Issues

**Symptoms:**
- "No space left on device"
- Containers won't start

**Solutions:**
```bash
# Check disk usage
df -h

# Clean Docker system
docker system prune -af --volumes

# Clean old logs
find /opt/travel-marketplace-backend/logs -name "*.log" -mtime +7 -delete

# Check large files
du -sh /opt/travel-marketplace-backend/* | sort -h
```

---

## Performance Tips

### 1. Database Optimization

```bash
# Regular vacuum (automated by PostgreSQL, but can be manual)
docker compose -f docker-compose.prod.yml exec db psql -U $SQL_USER -d $SQL_DATABASE -c "VACUUM ANALYZE;"

# Check index usage
docker compose -f docker-compose.prod.yml exec db psql -U $SQL_USER -d $SQL_DATABASE -c "SELECT schemaname, tablename, indexname, idx_scan FROM pg_stat_user_indexes ORDER BY idx_scan;"

# Add indexes for commonly queried fields
docker compose -f docker-compose.prod.yml exec api python manage.py dbshell
```

### 2. Cache Strategy

```python
# Use caching for expensive queries
from django.core.cache import cache

def get_tours(category):
    cache_key = f"tours_{category}"
    tours = cache.get(cache_key)
    
    if tours is None:
        tours = TourPackage.objects.filter(category=category)
        cache.set(cache_key, tours, 300)  # 5 minutes
    
    return tours
```

### 3. Background Tasks

```python
# Use Celery for slow operations
from celery import shared_task

@shared_task
def send_booking_confirmation(booking_id):
    # Send email asynchronously
    pass
```

### 4. Static Files

```bash
# Use CDN for static files (if possible)
# Or serve from Nginx efficiently

# Compress static files
docker compose -f docker-compose.prod.yml exec api python manage.py collectstatic --noinput
```

---

## Upgrade Path

### When to Upgrade

Consider upgrading if you experience:

1. **Consistent high memory usage** (>85% for extended periods)
2. **Frequent swap usage** (>25% of swap used regularly)
3. **Slow response times** (>1 second average)
4. **Container restarts** due to OOM
5. **Growing user base** (>100 concurrent users)

### Recommended Upgrade: 4GB RAM / 2 vCPU

With double the resources, you can:

```yaml
# docker-compose.prod.yml changes
api:
  command: gunicorn ... --workers 2 --threads 4
  resources:
    limits:
      memory: 512M

db:
  resources:
    limits:
      memory: 512M

redis:
  command: redis-server --maxmemory 256mb
  resources:
    limits:
      memory: 384M

celery:
  command: celery -A backend worker --concurrency=2
  resources:
    limits:
      memory: 512M
```

### Migration Steps

1. **Backup everything**
   ```bash
   ./deploy/backup.sh
   ```

2. **Resize droplet** (Digital Ocean)
   - Power off droplet
   - Resize to 4GB plan
   - Power on

3. **Update configuration**
   ```bash
   # Update docker-compose.prod.yml with higher limits
   vim docker-compose.prod.yml
   ```

4. **Redeploy**
   ```bash
   sudo ./deploy/deploy.sh
   ```

---

## Maintenance Checklist

### Daily
- [ ] Check `docker stats` for resource usage
- [ ] Monitor application logs for errors
- [ ] Verify API health endpoint

### Weekly
- [ ] Review slow query logs
- [ ] Check disk space usage
- [ ] Clean old Docker logs
- [ ] Verify backup completion

### Monthly
- [ ] Update system packages
- [ ] Review and optimize database indexes
- [ ] Analyze traffic patterns
- [ ] Consider scaling if needed

---

## Additional Resources

- [Django Performance Tips](https://docs.djangoproject.com/en/stable/topics/performance/)
- [PostgreSQL Performance](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Nginx Performance](https://www.nginx.com/blog/tuning-nginx/)
- [Digital Ocean Monitoring](https://docs.digitalocean.com/products/monitoring/)

---

## Support

If you encounter issues:

1. Check logs: `docker compose -f docker-compose.prod.yml logs -f`
2. Monitor resources: `docker stats` and `htop`
3. Review this guide's troubleshooting section
4. Check application-specific logs in `/opt/travel-marketplace-backend/logs/`

---

**Last Updated**: January 2026  
**Tested On**: Digital Ocean 2GB/1vCPU Droplet (Ubuntu 22.04)

