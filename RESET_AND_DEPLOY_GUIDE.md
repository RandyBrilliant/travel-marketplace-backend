# Complete Reset and Fresh Deployment Guide

This guide will help you completely reset Docker and do a fresh deployment from **any directory**.

## Your Setup

You're running from: `~/travel-marketplace-backend` (or wherever your folder is)  
NOT from `/opt/travel-marketplace-backend`

The scripts will automatically detect your current directory! ✅

## Step 1: Complete Reset (Ubuntu Server)

SSH into your server and run:

```bash
# Go to YOUR app directory (wherever it is)
cd ~/travel-marketplace-backend
# OR wherever you have the project

# Make the reset script executable
chmod +x deploy/complete-reset.sh

# Run the complete reset (WARNING: This deletes everything!)
sudo ./deploy/complete-reset.sh
```

**What this does:**
- Stops all Docker containers
- Removes all containers, volumes, networks, and images
- Cleans up Docker system
- Preserves your `.env` file and backups

## Step 2: Update Your Code

Pull the latest fixes with all the configuration changes:

```bash
cd ~/travel-marketplace-backend  # Or your directory

# Make sure you have the latest code
git pull
```

## Step 3: Prepare .env File

```bash
cd ~/travel-marketplace-backend  # Or your directory

# If .env doesn't exist, create it
cp env.prod.example .env

# Edit the .env file
nano .env
```

**Critical settings for .env:**

```bash
# Django Settings
SECRET_KEY=your-random-secret-key-here
DEBUG=0
ALLOWED_HOSTS=api.goholiday.id,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://api.goholiday.id,https://goholiday.id
CORS_ALLOWED_ORIGINS=https://goholiday.id,https://www.goholiday.id

# IMPORTANT: Set to false to avoid redirect loop!
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true

# Database (use strong passwords!)
SQL_ENGINE=django.db.backends.postgresql
SQL_DATABASE=travel_marketplace
SQL_USER=travel_user
SQL_PASSWORD=your-strong-password-here
SQL_HOST=db
SQL_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Email (Mailgun)
MAILGUN_SMTP_SERVER=smtp.mailgun.org
MAILGUN_SMTP_PORT=587
MAILGUN_SMTP_LOGIN=your-mailgun-login
MAILGUN_SMTP_PASSWORD=your-mailgun-password
DEFAULT_FROM_EMAIL=noreply@goholiday.id
FRONTEND_URL=https://goholiday.id
```

**Generate a secure SECRET_KEY:**

```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

## Step 4: Run Fresh Deployment

```bash
cd ~/travel-marketplace-backend  # Or your directory

# Make scripts executable
chmod +x deploy/*.sh

# Option A: Use the automated script (easiest!)
sudo ./deploy/fresh-start.sh

# Option B: Manual deployment
sudo ./deploy/deploy.sh
```

**The deploy script will automatically:**
1. Copy files to deployment directory
2. Create necessary directories
3. Pull Docker images
4. Build containers
5. Start all services
6. Run database migrations
7. Collect static files
8. Perform health checks

## Step 5: Create Superuser

```bash
cd ~/travel-marketplace-backend  # Or your directory

# Create admin user
docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser
```

## Step 6: Verify Everything Works

```bash
cd ~/travel-marketplace-backend  # Or your directory

# Check all containers are running
docker compose -f docker-compose.prod.yml ps

# Test the API
curl http://localhost/health/
curl https://api.goholiday.id/health/

# Check logs if there are issues
docker compose -f docker-compose.prod.yml logs -f
```

## Step 7: Test in Browser

Open your browser and go to:
- `https://api.goholiday.id/health/` - Should return JSON health status
- `https://api.goholiday.id/api/schema/` - Should show API documentation

## Troubleshooting

### If nginx keeps restarting:

```bash
# Check nginx logs
docker compose -f docker-compose.prod.yml logs nginx

# Most common issue: duplicate resolver
# The fixed config should have only ONE resolver directive
grep -n "resolver" nginx/api.goholiday.id.conf
```

### If you get "too many redirects":

```bash
# Check your .env
grep "SECURE_SSL_REDIRECT" .env

# It should be: SECURE_SSL_REDIRECT=false
# If not, fix it:
sed -i 's/SECURE_SSL_REDIRECT=true/SECURE_SSL_REDIRECT=false/' .env

# Restart API
docker compose -f docker-compose.prod.yml restart api
```

### If celery keeps restarting:

```bash
# Check celery logs
docker compose -f docker-compose.prod.yml logs celery

# The fixed docker-compose.prod.yml has increased memory limits
```

### Quick commands (run from YOUR project directory):

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs -f

# Restart a specific service
docker compose -f docker-compose.prod.yml restart api

# Check service status
docker compose -f docker-compose.prod.yml ps

# Restart everything
docker compose -f docker-compose.prod.yml restart

# Stop everything
docker compose -f docker-compose.prod.yml down

# Start everything
docker compose -f docker-compose.prod.yml up -d
```

## Files Fixed in This Update

1. **nginx/api.goholiday.id.conf** - Fixed duplicate resolver directive
2. **docker-compose.prod.yml** - Fixed nginx health check to use HTTP, increased celery memory
3. **deploy/complete-reset.sh** - Works from any directory
4. **deploy/fresh-start.sh** - Works from any directory
5. **deploy/deploy.sh** - Uses APP_DIR environment variable

## Environment Variable for Custom Directory

The deploy script uses `APP_DIR` environment variable. By default, it deploys to `/opt/travel-marketplace-backend`, but you can override it:

```bash
# If you want to deploy to a different directory
export APP_DIR="/home/yourusername/travel-marketplace-backend"
sudo -E ./deploy/deploy.sh
```

Or just run the scripts from your project directory - they'll auto-detect it!

## Common Issues Resolved

✅ Nginx duplicate resolver error  
✅ Nginx unhealthy status  
✅ Too many redirects error  
✅ Celery memory issues  
✅ SSL redirect loop  
✅ Scripts work from any directory  

Your deployment should now work perfectly from any location! 🎉
