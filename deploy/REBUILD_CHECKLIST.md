# Rebuild Checklist for 2GB/1vCPU Digital Ocean Server

This is your step-by-step checklist for rebuilding the travel marketplace on a fresh server with optimized configuration.

## ✅ Pre-Rebuild Checklist

### 1. Backup Everything (if applicable)
- [ ] Database backup
- [ ] Media files backup
- [ ] `.env` file backup
- [ ] SSL certificates backup (if applicable)

### 2. Server Access
- [ ] SSH access to server
- [ ] Root/sudo privileges confirmed
- [ ] Server specifications verified: 2GB RAM, 1 vCPU

## 🚀 Fresh Installation Steps

### Step 1: Initial Server Setup

```bash
# SSH into your server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Clone your repository (if not already done)
cd /opt
git clone https://github.com/yourusername/travel-marketplace-backend.git
cd travel-marketplace-backend
```

### Step 2: Run Complete Optimization

```bash
# This script does everything needed for 2GB optimization
sudo ./deploy/optimize-2gb.sh
```

**What this does:**
- ✓ Configures kernel memory settings
- ✓ Creates 2GB swap file
- ✓ Optimizes Docker daemon
- ✓ Sets up PostgreSQL configuration
- ✓ Optimizes Nginx for single vCPU
- ✓ Configures log rotation

### Step 3: Configure Environment

```bash
# Copy example environment file
cp env.prod.example .env

# Edit configuration
nano .env
```

**Critical settings to update:**
```bash
# Security
SECRET_KEY=<generate-random-key-here>
DEBUG=0

# Database
SQL_DATABASE=travel_marketplace
SQL_USER=travel_user
SQL_PASSWORD=<your-secure-password>

# Domain
ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com
CSRF_TRUSTED_ORIGINS=https://api.yourdomain.com,https://yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# Email (Mailgun)
MAILGUN_API_KEY=<your-mailgun-api-key>
MAILGUN_DOMAIN=yourdomain.com
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Frontend
FRONTEND_URL=https://yourdomain.com

# SSL (set to false initially, true after SSL setup)
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

### Step 4: Deploy Application

```bash
# Run deployment script
sudo ./deploy/deploy.sh
```

**What this does:**
- ✓ Copies files to `/opt/travel-marketplace-backend`
- ✓ Builds Docker images
- ✓ Starts all services
- ✓ Runs database migrations
- ✓ Collects static files
- ✓ Performs health checks

### Step 5: Create Superuser

```bash
# Create admin user for Django admin
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml exec api python manage.py createsuperuser
```

**Enter:**
- Username: admin
- Email: admin@yourdomain.com
- Password: (create a strong password)

### Step 6: Verify Deployment

```bash
# Check container status
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml ps

# All containers should show "healthy" or "running"

# Check resource usage
docker stats

# Test API
curl http://localhost/health/
# Should return: {"status": "healthy"}

# View logs if any issues
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml logs -f
```

## 🔐 Optional: SSL Setup

### Prerequisites
- Domain DNS configured (A record pointing to server IP)
- Port 80 accessible from internet

```bash
# Set email for SSL notifications
export SSL_EMAIL=admin@yourdomain.com

# Run SSL setup
sudo ./deploy/ssl-setup.sh
```

**After SSL is configured, update `.env`:**
```bash
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

**Restart services:**
```bash
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml restart
```

## 📊 Post-Deployment Monitoring

### First 24 Hours

Monitor these metrics closely:

```bash
# 1. Memory usage (should stay under 1.8GB)
watch -n 5 free -h

# 2. Container stats
docker stats

# 3. System load
htop

# 4. Application logs
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml logs -f
```

### What to Watch For

**Memory:**
- Total usage should be ~1.4-1.6GB
- Swap usage should be minimal (<500MB)
- If swap usage consistently >500MB, consider upgrading

**CPU:**
- Normal: 5-30% (idle to moderate load)
- Warning: >60% sustained
- Critical: >80% sustained

**Disk:**
- Check weekly: `df -h`
- Clean if >80%: `docker system prune -af`

## 🛠️ Common Post-Setup Tasks

### Database Management

```bash
# Reset database (WARNING: deletes all data)
sudo ./deploy/reset-database.sh

# Backup database
sudo ./deploy/backup.sh

# Manual backup
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml exec -T db \
  pg_dump -U travel_user travel_marketplace > backup-$(date +%Y%m%d).sql
```

### Log Management

```bash
# View application logs
tail -f /opt/travel-marketplace-backend/logs/django.log

# View container logs
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml logs -f api

# Clean old logs (automated by logrotate, but can be manual)
find /opt/travel-marketplace-backend/logs -name "*.log" -mtime +7 -delete
```

### Updates and Maintenance

```bash
# Update code
cd /opt/travel-marketplace-backend
git pull

# Redeploy
sudo ./deploy/deploy.sh

# Just restart services (no rebuild)
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml restart
```

## 📈 Resource Usage Expected Values

### Normal Operation (Idle)
```
Total Memory:  ~1.4GB / 2GB (70%)
Swap:          ~100MB / 2GB (5%)
CPU:           5-15%
Disk I/O:      Low
```

### Under Moderate Load (10-50 concurrent users)
```
Total Memory:  ~1.6GB / 2GB (80%)
Swap:          ~200MB / 2GB (10%)
CPU:           20-40%
Disk I/O:      Moderate
```

### Warning Thresholds
```
Memory:        >1.8GB (>90%) - Consider upgrade
Swap:          >500MB - Performance degraded
CPU:           >60% sustained - Consider upgrade
```

## 🔄 When to Consider Upgrading

### Upgrade to 4GB/2vCPU if:
- Memory usage consistently >85%
- Swap usage regularly >500MB
- CPU usage frequently >60%
- Response times >2 seconds
- Planning to scale beyond 100 concurrent users

### Benefits of Upgrading:
- 2× Gunicorn workers (better concurrency)
- 2× Celery workers (faster background tasks)
- More memory for caching
- Better response times
- Room for growth

## 📝 Quick Reference Commands

```bash
# Service Management
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml ps          # Status
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml restart     # Restart all
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml restart api # Restart API
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml logs -f     # View logs

# Resource Monitoring
docker stats              # Container resource usage
free -h                   # Memory usage
htop                      # System monitor
df -h                     # Disk usage

# Maintenance
sudo ./deploy/backup.sh   # Backup database
sudo ./deploy/deploy.sh   # Redeploy application
docker system prune -af   # Clean Docker system

# Database
sudo ./deploy/reset-database.sh  # Reset database (WARNING: deletes data)

# Optimization (run once after fresh install)
sudo ./deploy/optimize-2gb.sh    # Complete system optimization
```

## 📚 Documentation References

- **Complete Optimization Guide**: `./OPTIMIZATION_GUIDE_2GB.md`
- **Deployment Scripts**: `./README.md`
- **Quick Deploy**: `./QUICK_DEPLOY.md`
- **Full Deployment Guide**: `../DEPLOYMENT.md`

## ⚠️ Important Reminders

1. **Always backup before making changes**
2. **Monitor resource usage in first 24 hours**
3. **Set DEBUG=0 in production** (already done in .env)
4. **Use strong passwords** for database and admin
5. **Keep system updated**: `apt update && apt upgrade` monthly
6. **Monitor disk space**: Clean logs and Docker system regularly
7. **SSL certificates**: Renew automatically via certbot (check: `certbot renew --dry-run`)

## ✅ Post-Setup Verification Checklist

- [ ] All containers running and healthy
- [ ] API health check responding: `curl http://localhost/health/`
- [ ] Database accessible
- [ ] Superuser created
- [ ] Memory usage normal (~1.4-1.6GB)
- [ ] Swap configured and active
- [ ] Logs rotating properly
- [ ] SSL configured (if applicable)
- [ ] Domain resolving correctly
- [ ] Email sending working (test with password reset)
- [ ] File uploads working
- [ ] Celery tasks processing

## 🎉 You're Ready!

Your Travel Marketplace is now optimized and running on a 2GB/1vCPU server.

**Next Steps:**
1. Test all API endpoints
2. Create test bookings
3. Monitor for 24-48 hours
4. Set up automated backups (cron job)
5. Configure monitoring alerts (optional)

**Need Help?**
- Check logs: `docker compose logs -f`
- Review: `OPTIMIZATION_GUIDE_2GB.md`
- Monitor: `docker stats` and `htop`

---

**Last Updated**: January 2026  
**Optimized For**: Digital Ocean 2GB/1vCPU Droplet

