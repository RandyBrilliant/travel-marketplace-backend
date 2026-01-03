# Production Deployment Guide

This guide covers deploying the DCNetwork API to an Ubuntu server with Docker, Nginx, and SSL.

## Prerequisites

- Ubuntu 20.04 LTS or later
- Root or sudo access
- Domain name `api.goholiday.id` pointing to your server IP
- Minimum 2GB RAM, 2 CPU cores, 20GB disk space

## Architecture

```
┌─────────────────┐
│   Internet      │
└────────┬────────┘
         │
    ┌────▼────┐
    │  Nginx  │ (Port 80/443, SSL Termination)
    └────┬────┘
         │
    ┌────▼────┐
    │  API    │ (Django + Gunicorn)
    └────┬────┘
         │
    ┌────▼────┐
    │PostgreSQL│
    └─────────┘
```

## Step 1: Initial Server Setup

### 1.1 Connect to your server

```bash
ssh root@your-server-ip
```

### 1.2 Run the setup script

```bash
# Clone or upload the project to your server
cd /opt
git clone <your-repo-url> dcnetwork-api
# OR upload files via SCP/SFTP

cd dcnetwork-api/travel-marketplace-backend
chmod +x deploy/*.sh
sudo ./deploy/ubuntu-setup.sh
```

This script will:
- Update system packages
- Install Docker and Docker Compose
- Configure firewall (UFW)
- Create necessary directories
- Setup log rotation
- Create systemd service
- Setup SSL renewal cron job

## Step 2: Configure Environment

### 2.1 Create production environment file

```bash
cd /opt/dcnetwork-api/travel-marketplace-backend
cp env.prod.example .env
nano .env
```

### 2.2 Update required variables

**Critical settings to update:**

```bash
# Generate a secure secret key
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# Database credentials (use strong passwords!)
SQL_USER=travel_user
SQL_PASSWORD=your-strong-db-password
SQL_DATABASE=travel_marketplace

# Domain settings
ALLOWED_HOSTS=api.goholiday.id,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://api.goholiday.id,https://www.goholiday.id

# CORS (update with your frontend domain)
CORS_ALLOWED_ORIGINS=https://www.goholiday.id,https://goholiday.id

# Email configuration
MAILGUN_SMTP_LOGIN=your-mailgun-login
MAILGUN_SMTP_PASSWORD=your-mailgun-password
DEFAULT_FROM_EMAIL=noreply@goholiday.id
FRONTEND_URL=https://www.goholiday.id

# Security (production)
DEBUG=0
SECURE_SSL_REDIRECT=true
```

## Step 3: DNS Configuration

Before proceeding, ensure your DNS is configured:

1. Add an A record:
   ```
   Type: A
   Name: api
   Value: your-server-ip
   TTL: 3600
   ```

2. Verify DNS propagation:
   ```bash
   dig api.goholiday.id
   # Should return your server IP
   ```

## Step 4: SSL Certificate Setup

### 4.1 Run SSL setup script

```bash
cd /opt/dcnetwork-api/travel-marketplace-backend
sudo ./deploy/ssl-setup.sh
```

**Note:** You may need to set the email:
```bash
export SSL_EMAIL=admin@goholiday.id
sudo -E ./deploy/ssl-setup.sh
```

This script will:
- Verify DNS configuration
- Request Let's Encrypt certificate
- Copy certificates to nginx directory
- Setup auto-renewal

## Step 5: Deploy Application

### 5.1 Run deployment script

```bash
cd /opt/dcnetwork-api/travel-marketplace-backend
./deploy/deploy.sh
```

This script will:
- Copy files to deployment directory
- Build Docker images
- Start all services
- Run database migrations
- Collect static files
- Perform health checks

### 5.2 Create superuser

```bash
cd /opt/dcnetwork-api
docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser
```

## Step 6: Verify Deployment

### 6.1 Check service status

```bash
cd /opt/dcnetwork-api
docker compose -f docker-compose.prod.yml ps
```

All services should show "Up" status.

### 6.2 Test endpoints

```bash
# Health check
curl https://api.goholiday.id/health/

# API documentation
curl https://api.goholiday.id/api/schema/
```

### 6.3 Check logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f nginx
```

## Step 7: Setup Automated Backups

### 7.1 Test backup script

```bash
cd /opt/dcnetwork-api/travel-marketplace-backend
./deploy/backup.sh
```

### 7.2 Schedule daily backups

```bash
crontab -e
```

Add:
```cron
0 2 * * * /opt/dcnetwork-api/travel-marketplace-backend/deploy/backup.sh >> /var/log/dcnetwork-api-backup.log 2>&1
```

## Management Commands

### Start/Stop Services

```bash
cd /opt/dcnetwork-api

# Start
docker compose -f docker-compose.prod.yml up -d

# Stop
docker compose -f docker-compose.prod.yml down

# Restart
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart api
```

### View Logs

```bash
# All logs
docker compose -f docker-compose.prod.yml logs -f

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100

# Specific service
docker compose -f docker-compose.prod.yml logs -f api
```

### Database Management

```bash
# Access database
docker compose -f docker-compose.prod.yml exec db psql -U travel_user -d travel_marketplace

# Run migrations
docker compose -f docker-compose.prod.yml exec api python manage.py migrate

# Create superuser
docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser

# Django shell
docker compose -f docker-compose.prod.yml exec api python manage.py shell
```

### Update Application

```bash
cd /opt/dcnetwork-api/travel-marketplace-backend

# Pull latest code
git pull origin main

# Run deployment
./deploy/deploy.sh
```

## Monitoring

### Health Checks

- API: `https://api.goholiday.id/health/`
- Nginx: Built-in health check on port 80

### Resource Usage

```bash
# Container stats
docker stats

# Disk usage
df -h
docker system df

# Log sizes
du -sh /opt/dcnetwork-api/logs/*
```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs

# Check container status
docker compose -f docker-compose.prod.yml ps -a

# Restart services
docker compose -f docker-compose.prod.yml restart
```

### SSL certificate issues

```bash
# Check certificate
certbot certificates

# Renew manually
certbot renew --force-renewal

# Check nginx SSL config
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```

### Database connection errors

```bash
# Check database status
docker compose -f docker-compose.prod.yml exec db pg_isready -U travel_user

# Check database logs
docker compose -f docker-compose.prod.yml logs db
```

### Permission issues

```bash
# Fix media directory permissions
sudo chown -R 1000:1000 /opt/dcnetwork-api/media
sudo chmod -R 755 /opt/dcnetwork-api/media
```

## Security Checklist

- [ ] Changed all default passwords
- [ ] Set `DEBUG=0` in production
- [ ] Configured strong `SECRET_KEY`
- [ ] Updated `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
- [ ] SSL certificate installed and auto-renewal configured
- [ ] Firewall (UFW) configured
- [ ] Regular backups scheduled
- [ ] Log rotation configured
- [ ] Non-root user for containers
- [ ] Security headers enabled in Nginx

## Backup and Restore

### Manual Backup

```bash
./deploy/backup.sh
```

Backups are stored in `/opt/dcnetwork-api/backups/`

### Restore Database

```bash
# Stop services
docker compose -f docker-compose.prod.yml down

# Restore database
gunzip < backups/backup-YYYYMMDD-HHMMSS/database.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U travel_user -d travel_marketplace

# Start services
docker compose -f docker-compose.prod.yml up -d
```

### Restore Media Files

```bash
cd /opt/dcnetwork-api
tar -xzf backups/backup-YYYYMMDD-HHMMSS/media.tar.gz
```

## Scaling

### Increase API Workers

Edit `docker-compose.prod.yml`:
```yaml
api:
  command: gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 8 --threads 2
```

### Add More Celery Workers

```yaml
celery:
  deploy:
    replicas: 3
```

## Support

For issues or questions:
- Check logs: `docker compose -f docker-compose.prod.yml logs`
- Review this documentation
- Check Django logs: `/opt/dcnetwork-api/logs/django.log`

