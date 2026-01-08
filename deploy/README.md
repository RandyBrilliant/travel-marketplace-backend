# Deployment Scripts

This directory contains scripts for deploying the Travel Marketplace Backend to production.

## Scripts Overview

### `ubuntu-setup.sh`
Initial server setup script. Run this once on a fresh Ubuntu server.

**What it does:**
- Installs Docker and Docker Compose
- Configures firewall (UFW)
- Creates necessary directories
- Sets up log rotation
- Creates systemd service
- Configures SSL renewal cron job

**Usage:**
```bash
sudo ./deploy/ubuntu-setup.sh
```

### `ssl-setup.sh`
Sets up Let's Encrypt SSL certificate for `api.goholiday.id`.

**Prerequisites:**
- DNS must be configured (A record pointing to server IP)
- Port 80 must be accessible

**Usage:**
```bash
export SSL_EMAIL=admin@goholiday.id  # Optional
sudo ./deploy/ssl-setup.sh
```

### `deploy.sh`
Deploys the application to production.

**What it does:**
- Copies files to deployment directory
- Builds Docker images
- Starts all services
- Runs database migrations
- Collects static files
- Performs health checks

**Usage:**
```bash
./deploy/deploy.sh
```

### `backup.sh`
Creates backups of database and media files.

**What it backs up:**
- PostgreSQL database (compressed)
- Media files
- Configuration (sanitized)

**Usage:**
```bash
./deploy/backup.sh
```

**Scheduling:**
Add to crontab for daily backups:
```bash
0 2 * * * /opt/travel-marketplace-backend/deploy/backup.sh
```

### `update.sh`
Quick update script for deploying code changes to production.

**What it does:**
- Pulls latest code (if git repository)
- Stops all containers
- Rebuilds Docker images
- Starts services
- Runs migrations
- Collects static files

**⚠️ Note:** Causes ~30-60 seconds of downtime

**Usage:**
```bash
sudo ./deploy/update.sh
```

### `rolling-update.sh`
Rolling update with minimal downtime (recommended for production).

**What it does:**
- Updates services one by one
- Keeps services running during update
- Minimal user impact (~2-5 seconds)

**Usage:**
```bash
sudo ./deploy/rolling-update.sh
```

**See:** `deploy/UPDATE_GUIDE.md` for complete update strategies

### `reset-database.sh`
Resets the database in Docker production environment.

**What it does:**
- Optionally creates a backup before reset
- Drops all database tables
- Runs migrations to recreate the schema
- Optionally creates a superuser

**⚠️ WARNING:** This will delete all data in the database!

**Usage:**
```bash
sudo ./deploy/reset-database.sh
```

**Alternative manual method:**
```bash
# Connect to database container and drop/recreate
docker compose -f docker-compose.prod.yml exec db psql -U <user> -d postgres -c "DROP DATABASE IF EXISTS <database>;"
docker compose -f docker-compose.prod.yml exec db psql -U <user> -d postgres -c "CREATE DATABASE <database>;"

# Run migrations
docker compose -f docker-compose.prod.yml exec api python manage.py migrate

# Create superuser
docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser
```

## Deployment Workflow

1. **Initial Setup** (one-time)
   ```bash
   sudo ./deploy/ubuntu-setup.sh
   ```

2. **Configure Environment**
   ```bash
   cp env.prod.example .env
   nano .env  # Edit with your settings
   ```

3. **Setup SSL** (after DNS is configured)
   ```bash
   sudo ./deploy/ssl-setup.sh
   ```

4. **Deploy Application**
   ```bash
   ./deploy/deploy.sh
   ```

5. **Create Superuser**
   ```bash
   docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser
   ```

6. **Schedule Backups**
   ```bash
   crontab -e
   # Add: 0 2 * * * /opt/travel-marketplace-backend/deploy/backup.sh
   ```

## Environment Variables

See `env.prod.example` for all required environment variables.

**Critical variables:**
- `SECRET_KEY` - Must be set to a secure random value
- `SQL_PASSWORD` - Strong database password
- `ALLOWED_HOSTS` - Must include `api.goholiday.id`
- `DEBUG=0` - Must be 0 in production

## Troubleshooting

### Scripts won't run
```bash
chmod +x deploy/*.sh
```

### SSL certificate fails
- Verify DNS is configured correctly
- Check port 80 is accessible
- Ensure domain resolves to server IP

### Deployment fails
- Check `.env` file is configured correctly
- Verify Docker is running: `docker ps`
- Check logs: `docker compose -f docker-compose.prod.yml logs`

### Services won't start
- Check logs: `docker compose -f docker-compose.prod.yml logs`
- Verify database credentials in `.env`
- Check disk space: `df -h`

## File Structure

```
deploy/
├── ubuntu-setup.sh             # Initial server setup
├── ssl-setup.sh                # SSL certificate setup
├── deploy.sh                   # Application deployment
├── backup.sh                   # Backup script
├── reset-database.sh           # Database reset script
├── complete-reset.sh           # Complete Docker reset (removes everything)
├── fresh-start.sh              # Fresh deployment after reset
├── optimize-2gb.sh             # Complete 2GB RAM optimization
├── fix-2gb-memory.sh           # Legacy memory fix script
├── README.md                   # This file
├── QUICK_DEPLOY.md             # Quick reference guide
└── OPTIMIZATION_GUIDE_2GB.md   # Complete optimization guide for 2GB servers
```

## Optimization for Low-Resource Servers

### For 2GB RAM / 1 vCPU Servers (Digital Ocean, etc.)

If you're running on a server with limited resources, run the optimization script:

```bash
sudo ./deploy/optimize-2gb.sh
```

This will:
- Configure system memory settings
- Set up swap space
- Optimize Docker daemon
- Configure PostgreSQL for low memory
- Optimize Nginx settings
- Set up log rotation

For complete details, see: **[OPTIMIZATION_GUIDE_2GB.md](./OPTIMIZATION_GUIDE_2GB.md)**

## Support

For detailed deployment instructions, see `../DEPLOYMENT.md`

