# Custom Directory Setup Guide

Your deployment is at: `/home/regretzz/travel-marketplace-backend`

The default scripts assume `/opt/travel-marketplace-backend`, but they support custom directories via environment variables.

## 🎯 Quick Setup for Your Custom Directory

### Option 1: Use Environment Variable (Recommended)

Set `APP_DIR` before running any deploy scripts:

```bash
export APP_DIR=/home/regretzz/travel-marketplace-backend
```

**To make it permanent** (add to your shell profile):

```bash
# Add to ~/.bashrc or ~/.bash_profile
echo 'export APP_DIR=/home/regretzz/travel-marketplace-backend' >> ~/.bashrc
source ~/.bashrc
```

### Option 2: Pass APP_DIR Inline

```bash
# For each command
APP_DIR=/home/regretzz/travel-marketplace-backend sudo -E ./deploy/deploy.sh
APP_DIR=/home/regretzz/travel-marketplace-backend sudo -E ./deploy/optimize-2gb.sh
```

The `-E` flag preserves environment variables when using sudo.

## 📋 Complete Rebuild Steps for Your Setup

### Step 1: Initial Setup (One-Time)

```bash
# Navigate to your directory
cd /home/regretzz/travel-marketplace-backend

# Set APP_DIR permanently
echo 'export APP_DIR=/home/regretzz/travel-marketplace-backend' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $APP_DIR
# Should output: /home/regretzz/travel-marketplace-backend
```

### Step 2: Run Optimization

```bash
# Run with custom directory
sudo -E ./deploy/optimize-2gb.sh
```

**What this does:**
- Uses your custom directory: `/home/regretzz/travel-marketplace-backend`
- Configures system for 2GB RAM
- Sets up swap, PostgreSQL config, etc.

### Step 3: Configure Environment

```bash
# Copy and edit .env
cp env.prod.example .env
nano .env
```

**Update these critical values:**

```bash
# Security
SECRET_KEY=<generate-random-key>
DEBUG=0

# Database
SQL_DATABASE=travel_marketplace
SQL_USER=travel_user
SQL_PASSWORD=<your-secure-password>

# Domain
ALLOWED_HOSTS=api.goholiday.id,localhost
CSRF_TRUSTED_ORIGINS=https://api.goholiday.id
CORS_ALLOWED_ORIGINS=https://goholiday.id,https://www.goholiday.id

# Email
MAILGUN_API_KEY=<your-key>
MAILGUN_DOMAIN=goholiday.id
DEFAULT_FROM_EMAIL=noreply@goholiday.id

# Frontend
FRONTEND_URL=https://www.goholiday.id

# SSL (false initially, true after SSL setup)
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

### Step 4: Deploy Application

```bash
# Deploy with custom directory
cd /home/regretzz/travel-marketplace-backend
sudo -E ./deploy/deploy.sh
```

The script will:
- Use `/home/regretzz/travel-marketplace-backend` as source
- Copy to the same location (no rsync needed since you're already there)
- Build and start containers
- Run migrations

### Step 5: Create Superuser

```bash
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml exec api python manage.py createsuperuser
```

### Step 6: Verify Deployment

```bash
# Check containers
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml ps

# Test API
curl http://localhost/health/

# Monitor resources
docker stats
```

### Step 7: Setup SSL (After HTTP Works)

```bash
# Set email for SSL notifications
export SSL_EMAIL=admin@goholiday.id

# Run SSL setup
cd /home/regretzz/travel-marketplace-backend
sudo -E ./deploy/ssl-setup.sh
```

### Step 8: Enable SSL in Django

```bash
# Edit .env
nano /home/regretzz/travel-marketplace-backend/.env

# Update:
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true

# Restart services
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml restart
```

## 🔧 Modified Deploy Script (Alternative)

If you want to modify the scripts to hardcode your path, edit them:

### Update deploy.sh

```bash
nano /home/regretzz/travel-marketplace-backend/deploy/deploy.sh
```

Change line 14:
```bash
# From:
APP_DIR="${APP_DIR:-/opt/travel-marketplace-backend}"

# To:
APP_DIR="${APP_DIR:-/home/regretzz/travel-marketplace-backend}"
```

### Update optimize-2gb.sh

```bash
nano /home/regretzz/travel-marketplace-backend/deploy/optimize-2gb.sh
```

Change line 29:
```bash
# From:
APP_DIR="${APP_DIR:-/opt/travel-marketplace-backend}"

# To:
APP_DIR="${APP_DIR:-/home/regretzz/travel-marketplace-backend}"
```

### Update ssl-setup.sh

```bash
nano /home/regretzz/travel-marketplace-backend/deploy/ssl-setup.sh
```

No changes needed - it auto-detects the directory from script location.

## 📝 Quick Reference Commands (Your Custom Path)

### Service Management

```bash
# Base path for all commands
BASE=/home/regretzz/travel-marketplace-backend

# Container status
docker compose -f $BASE/docker-compose.prod.yml ps

# View logs
docker compose -f $BASE/docker-compose.prod.yml logs -f

# Restart services
docker compose -f $BASE/docker-compose.prod.yml restart

# Stop services
docker compose -f $BASE/docker-compose.prod.yml down

# Start services
docker compose -f $BASE/docker-compose.prod.yml up -d
```

### Database Management

```bash
# Reset database
cd /home/regretzz/travel-marketplace-backend
sudo -E ./deploy/reset-database.sh

# Backup database
sudo -E ./deploy/backup.sh

# Run migrations
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml exec api python manage.py migrate
```

### Deployment

```bash
# Full deployment
cd /home/regretzz/travel-marketplace-backend
sudo -E ./deploy/deploy.sh

# Just rebuild containers
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml up -d --build

# Just restart
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml restart
```

### Monitoring

```bash
# Container stats
docker stats

# System memory
free -h

# Disk usage
df -h

# Application logs
tail -f /home/regretzz/travel-marketplace-backend/logs/django.log
```

## 🚀 One-Command Deployment (Custom Path)

Create an alias for convenience:

```bash
# Add to ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# Travel Marketplace aliases
export APP_DIR=/home/regretzz/travel-marketplace-backend
alias tm-deploy='cd $APP_DIR && sudo -E ./deploy/deploy.sh'
alias tm-update='cd $APP_DIR && sudo -E ./deploy/rolling-update.sh'
alias tm-quick-update='cd $APP_DIR && sudo -E ./deploy/update.sh'
alias tm-logs='docker compose -f $APP_DIR/docker-compose.prod.yml logs -f'
alias tm-ps='docker compose -f $APP_DIR/docker-compose.prod.yml ps'
alias tm-restart='docker compose -f $APP_DIR/docker-compose.prod.yml restart'
alias tm-reload='docker compose -f $APP_DIR/docker-compose.prod.yml restart api celery'
alias tm-stats='docker stats'
alias tm-backup='cd $APP_DIR && sudo -E ./deploy/backup.sh'
alias tm-db-reset='cd $APP_DIR && sudo -E ./deploy/reset-database.sh'
EOF

# Reload
source ~/.bashrc
```

**Now you can use:**

```bash
tm-deploy      # Deploy application
tm-logs        # View logs
tm-ps          # Container status
tm-restart     # Restart services
tm-stats       # Resource usage
tm-backup      # Backup database
tm-db-reset    # Reset database
```

## ⚠️ Important Notes for Your Setup

### 1. File Permissions

Make sure your user owns the directory:

```bash
# Check ownership
ls -la /home/regretzz/ | grep travel-marketplace-backend

# Should show: drwxr-xr-x ... regretzz regretzz ... travel-marketplace-backend

# If not, fix it:
sudo chown -R regretzz:regretzz /home/regretzz/travel-marketplace-backend
```

### 2. Script Permissions

Make scripts executable:

```bash
cd /home/regretzz/travel-marketplace-backend
chmod +x deploy/*.sh entrypoint.sh
```

### 3. Docker Access

Your user needs Docker permissions:

```bash
# Add user to docker group
sudo usermod -aG docker regretzz

# Logout and login again for changes to take effect
# Or use: newgrp docker
```

### 4. Log Rotation

Update logrotate config for custom path:

```bash
# Edit logrotate config (if already created by optimize-2gb.sh)
sudo nano /etc/logrotate.d/travel-marketplace
```

Change:
```
# From:
/opt/travel-marketplace-backend/logs/*.log {

# To:
/home/regretzz/travel-marketplace-backend/logs/*.log {
```

## 📂 Directory Structure

Your setup at `/home/regretzz/travel-marketplace-backend`:

```
/home/regretzz/travel-marketplace-backend/
├── docker-compose.prod.yml        # Docker services
├── .env                           # Environment variables (create from env.prod.example)
├── deploy/
│   ├── deploy.sh                  # Main deployment script
│   ├── optimize-2gb.sh            # System optimization
│   ├── ssl-setup.sh               # SSL certificate setup
│   ├── reset-database.sh          # Database reset
│   └── backup.sh                  # Backup script
├── nginx/
│   ├── nginx.conf                 # Main Nginx config
│   ├── api.goholiday.id.conf      # SSL site config
│   ├── api.goholiday.id.http-only.conf  # HTTP-only config
│   └── ssl/
│       └── api.goholiday.id/      # SSL certificates (after SSL setup)
├── logs/
│   └── django.log                 # Application logs
├── media/                         # User uploads
└── staticfiles/                   # Static files (CSS, JS)
```

## ✅ Verification Checklist

After deployment:

```bash
# 1. Check APP_DIR variable
echo $APP_DIR
# Should show: /home/regretzz/travel-marketplace-backend

# 2. Check containers
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml ps
# All should be "Up" or "healthy"

# 3. Test API
curl http://localhost/health/
# Should return: {"status":"healthy"}

# 4. Check logs
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml logs -f api
# Should show no errors

# 5. Monitor resources
docker stats
# Memory should be ~1.4-1.6GB total

# 6. Check disk usage
df -h /home/regretzz
# Make sure you have space
```

## 🔄 Quick Rebuild Flow (Your Setup)

Complete rebuild from scratch:

```bash
# 1. Set environment
export APP_DIR=/home/regretzz/travel-marketplace-backend
cd $APP_DIR

# 2. Optimize system (one-time)
sudo -E ./deploy/optimize-2gb.sh

# 3. Configure environment
cp env.prod.example .env
nano .env  # Edit configuration

# 4. Deploy
sudo -E ./deploy/deploy.sh

# 5. Create superuser
docker compose -f $APP_DIR/docker-compose.prod.yml exec api python manage.py createsuperuser

# 6. Setup SSL (after DNS configured)
export SSL_EMAIL=admin@goholiday.id
sudo -E ./deploy/ssl-setup.sh

# 7. Enable SSL in Django
nano .env  # Set SECURE_SSL_REDIRECT=true, etc.
docker compose -f $APP_DIR/docker-compose.prod.yml restart

# 8. Test
curl https://api.goholiday.id/health/
```

## 🎉 All Set!

Your custom directory setup is ready. All scripts will work with your path at `/home/regretzz/travel-marketplace-backend` as long as you:

1. Export `APP_DIR` (or use `-E` with sudo)
2. Use full paths in docker compose commands
3. Ensure proper file permissions

**Pro tip:** Add the aliases to your `.bashrc` for easier management!

---

**Need help?** All scripts support `--help` or just read the comments at the top of each script.

