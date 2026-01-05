# Running on 2GB RAM Server

## The Problem

Your DigitalOcean droplet has **1 vCPU and 2GB RAM**, which is at the minimum edge for running this stack. The celery-beat container is being killed with **exit code 137 (OOM - Out of Memory)**.

### Memory Breakdown

**Original Configuration:**
```
API:         256M
Database:    256M
Redis:       128M
Celery:      256M
Celery Beat:  64M
Nginx:       ~20M
-----------------------
Total:       ~980M containers
             ~400M OS + Docker overhead
-----------------------
TOTAL:       ~1.38GB / 2GB (69% utilization)
```

This leaves only **~620MB** of breathing room, which gets exhausted under load or during deployments.

## The Solution

### Option 1: Optimize Configuration (Quick Fix) ⭐

Use the memory-optimized configuration designed for 2GB servers:

```bash
cd ~/travel-marketplace-backend
sudo ./deploy/fix-2gb-memory.sh
```

**What it does:**
- Fixes Redis memory warning
- Reduces Gunicorn workers: 2 → 1
- Reduces Celery concurrency: 2 → 1
- Lowers memory limits across all services
- Total container memory: ~850MB (130MB saved)

**Optimized Configuration:**
```
API:         200M (was 256M) - 1 worker
Database:    200M (was 256M)
Redis:       100M (was 128M) - 80MB max
Celery:      200M (was 256M) - 1 concurrency
Celery Beat: 100M (was 64M) ⬆ increased for stability
Nginx:        50M (was unlimited)
-----------------------
Total:       ~850M containers
             ~400M OS + Docker overhead
-----------------------
TOTAL:       ~1.25GB / 2GB (62% utilization)
```

**Trade-offs:**
- ✅ Stable operation
- ✅ No OOM kills
- ⚠️ Reduced throughput (1 worker vs 2)
- ⚠️ Slower under concurrent load

### Option 2: Upgrade Server (Recommended) 🚀

Upgrade to **4GB RAM** ($12-24/month on DigitalOcean):

**Benefits:**
- Full 2-worker configuration
- Better performance under load
- Room for growth
- No compromises

```bash
# On DigitalOcean
1. Go to your Droplet
2. Click "Resize"
3. Choose 4GB plan
4. Reboot
5. Run: sudo ./deploy/update.sh
```

### Option 3: Manual Optimization

If you want to manually optimize:

1. **Reduce Gunicorn workers in docker-compose.prod.yml:**
   ```yaml
   command: gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 2
   ```

2. **Reduce Celery concurrency:**
   ```yaml
   command: celery -A backend worker --loglevel=info --concurrency=1
   ```

3. **Increase celery-beat memory:**
   ```yaml
   celery-beat:
     deploy:
       resources:
         limits:
           memory: 100M
   ```

4. **Fix Redis warning:**
   ```bash
   sudo sysctl vm.overcommit_memory=1
   sudo bash -c 'echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf'
   ```

5. **Apply changes:**
   ```bash
   cd /opt/travel-marketplace-backend
   sudo docker compose -f docker-compose.prod.yml down
   sudo docker compose -f docker-compose.prod.yml up -d
   ```

## Monitoring

### Check Memory Usage

```bash
# Real-time container stats
docker stats

# Check system memory
free -h

# Check if OOM killer is active
dmesg | grep -i oom
```

### Check for Issues

```bash
# Container status
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml ps

# View logs
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml logs -f

# Check specific service
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml logs celery-beat
```

## When to Upgrade

You should upgrade to 4GB RAM if you experience:

- ❌ Frequent OOM kills
- ❌ Slow response times under load
- ❌ Services restarting unexpectedly
- ❌ Multiple concurrent users
- ❌ Large file uploads
- ❌ Heavy database queries

## Cost Comparison

| Provider | 2GB RAM | 4GB RAM | Difference |
|----------|---------|---------|------------|
| DigitalOcean | $12/mo | $24/mo | +$12/mo |
| Linode | $12/mo | $24/mo | +$12/mo |
| Vultr | $12/mo | $24/mo | +$12/mo |

**💡 Tip:** $12/month more for 2x memory is worth it for production workloads.

## Quick Commands

```bash
# Apply 2GB optimization
sudo ./deploy/fix-2gb-memory.sh

# Check memory usage
docker stats

# View all logs
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml logs -f

# Restart a specific service
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml restart celery-beat

# Check health
curl http://localhost/health/
```

## Additional Optimizations

### 1. Enable Swap (Emergency buffer)

```bash
# Create 2GB swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Adjust swappiness (lower = less swap usage)
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

⚠️ **Note:** Swap helps prevent crashes but is MUCH slower than RAM. Not a long-term solution.

### 2. Reduce Log Retention

```bash
# Limit Docker log sizes
sudo bash -c 'cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF'

sudo systemctl restart docker
```

### 3. Clean Up Docker

```bash
# Remove unused images and containers
docker system prune -a -f

# Remove unused volumes (careful!)
docker volume prune -f
```

## Troubleshooting

### Celery Beat keeps restarting

**Symptom:** `celery-beat exited with code 137`

**Cause:** Out of memory (OOM killed)

**Fix:** 
```bash
sudo ./deploy/fix-2gb-memory.sh
```

### Redis Warning

**Symptom:** `WARNING Memory overcommit must be enabled!`

**Fix:**
```bash
sudo sysctl vm.overcommit_memory=1
sudo bash -c 'echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf'
```

### Containers stuck in "health: starting"

**Cause:** Health checks not passing (usually due to slow startup on limited resources)

**Fix:** Wait 60-90 seconds after deployment for all services to stabilize.

## Summary

**For 2GB RAM:**
1. Run `sudo ./deploy/fix-2gb-memory.sh`
2. Monitor with `docker stats`
3. Consider adding swap as safety net

**For Production:**
1. Upgrade to 4GB RAM ($12-24 more/month)
2. Much better performance and stability
3. Room for future growth

**Remember:** 2GB is minimal. It works, but you're on the edge. 4GB+ is recommended for production.

