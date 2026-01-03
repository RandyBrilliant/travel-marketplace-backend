# Deployment Guide - Starting from New Ubuntu User

This guide walks you through deploying the backend after you've created a new user on your Ubuntu server.

## Prerequisites Checklist

- [ ] Ubuntu server (20.04 LTS or later)
- [ ] New user created with sudo privileges
- [ ] SSH access to the server
- [ ] Domain name `api.goholiday.id` (or your domain) configured

## Step 1: Connect to Your Server

```bash
# Connect via SSH
ssh your-username@your-server-ip
```

## Step 2: Install Git (if not already installed)

```bash
sudo apt-get update
sudo apt-get install -y git
```

## Step 3: Clone or Transfer Your Code

**Option A: Clone from Git Repository**
```bash
# Navigate to a suitable directory
cd /opt
sudo git clone <your-repository-url> dcnetwork-api
sudo chown -R $USER:$USER dcnetwork-api
cd dcnetwork-api/travel-marketplace-backend
```

**Option B: Transfer via SCP (from your local machine)**
```bash
# On your local machine
scp -r travel-marketplace-backend your-username@your-server-ip:/opt/dcnetwork-api/
```

Then on the server:
```bash
cd /opt/dcnetwork-api/travel-marketplace-backend
```

## Step 4: Make Scripts Executable

```bash
chmod +x deploy/*.sh
chmod +x entrypoint.sh
```

## Step 5: Run Initial Server Setup

This script will install Docker, configure firewall, and set up the environment:

```bash
sudo ./deploy/ubuntu-setup.sh
```

**What this does:**
- Updates system packages
- Installs Docker and Docker Compose
- Configures UFW firewall (allows SSH, HTTP, HTTPS)
- Creates necessary directories (`/opt/dcnetwork-api`)
- Sets up log rotation
- Creates systemd service for auto-start
- Sets up SSL renewal cron job

## Step 6: Configure Environment Variables

Create your production environment file:

```bash
cp env.prod.example .env
nano .env  # or use vi/vim
```

**Critical variables to update:**

1. **SECRET_KEY** - Generate a secure key:
   ```bash
   python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```
   Copy the output and set it as `SECRET_KEY=...` in `.env`

2. **Database credentials:**
   ```
   SQL_USER=travel_user
   SQL_PASSWORD=your-strong-random-password-here
   SQL_DATABASE=travel_marketplace
   ```

3. **Domain settings** (adjust if using a different domain):
   ```
   ALLOWED_HOSTS=api.goholiday.id,localhost,127.0.0.1
   CSRF_TRUSTED_ORIGINS=https://api.goholiday.id,https://www.goholiday.id
   CORS_ALLOWED_ORIGINS=https://www.goholiday.id,https://goholiday.id
   ```

4. **Email configuration** (Mailgun):
   ```
   MAILGUN_SMTP_LOGIN=your-mailgun-login
   MAILGUN_SMTP_PASSWORD=your-mailgun-password
   DEFAULT_FROM_EMAIL=noreply@goholiday.id
   FRONTEND_URL=https://www.goholiday.id
   ```

5. **Production settings:**
   ```
   DEBUG=0
   SECURE_SSL_REDIRECT=true
   ```

Save the file (in nano: Ctrl+X, then Y, then Enter)

## Step 7: Configure DNS (If Not Done)

Before setting up SSL, ensure your DNS is configured:

1. Add an A record in your DNS provider:
   ```
   Type: A
   Name: api (or @ if using root domain)
   Value: your-server-ip-address
   TTL: 3600
   ```

2. Verify DNS propagation (can take a few minutes to hours):
   ```bash
   dig api.goholiday.id
   # or
   nslookup api.goholiday.id
   ```

   The result should show your server's IP address.

## Step 8: Setup SSL Certificate

**IMPORTANT:** Only run this after DNS is configured and pointing to your server!

```bash
# Optionally set your email for Let's Encrypt
export SSL_EMAIL=admin@goholiday.id

# Run SSL setup
sudo ./deploy/ssl-setup.sh
```

This will:
- Verify DNS configuration
- Request Let's Encrypt SSL certificate
- Copy certificates to nginx directory
- Set up auto-renewal

**If DNS is not ready yet**, skip this step and come back after DNS propagates. You can deploy without SSL first (HTTP only) for testing, but SSL is required for production.

## Step 9: Deploy the Application

```bash
./deploy/deploy.sh
```

This script will:
- Copy files to `/opt/dcnetwork-api`
- Build Docker images
- Start all services (nginx, api, db, redis, celery)
- Run database migrations
- Collect static files
- Perform health checks

**Note:** First deployment may take 5-10 minutes to build images.

## Step 10: Create Superuser

After deployment, create a Django admin superuser:

```bash
cd /opt/dcnetwork-api
docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser
```

Follow the prompts to create your admin account.

## Step 11: Verify Deployment

### Check Service Status

```bash
cd /opt/dcnetwork-api
docker compose -f docker-compose.prod.yml ps
```

All services should show "Up" status.

### Test Health Endpoint

```bash
# If SSL is configured
curl https://api.goholiday.id/health/

# Or locally
curl http://localhost/health/
```

You should get a JSON response with status information.

### Check Logs

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f nginx
docker compose -f docker-compose.prod.yml logs -f db
```

Press `Ctrl+C` to exit log viewing.

## Step 12: Setup Automated Backups (Recommended)

Test the backup script:

```bash
cd /opt/dcnetwork-api/travel-marketplace-backend
./deploy/backup.sh
```

Schedule daily backups:

```bash
crontab -e
```

Add this line (backups run at 2 AM daily):
```
0 2 * * * /opt/dcnetwork-api/travel-marketplace-backend/deploy/backup.sh >> /var/log/dcnetwork-api-backup.log 2>&1
```

Save and exit.

## Common Commands Reference

### Service Management

```bash
cd /opt/dcnetwork-api

# Start services
docker compose -f docker-compose.prod.yml up -d

# Stop services
docker compose -f docker-compose.prod.yml down

# Restart services
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart api
```

### Database Operations

```bash
# Run migrations
docker compose -f docker-compose.prod.yml exec api python manage.py migrate

# Django shell
docker compose -f docker-compose.prod.yml exec api python manage.py shell

# Access PostgreSQL
docker compose -f docker-compose.prod.yml exec db psql -U travel_user -d travel_marketplace
```

### Viewing Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100

# Specific service
docker compose -f docker-compose.prod.yml logs -f api
```

### Updating the Application

```bash
cd /opt/dcnetwork-api/travel-marketplace-backend

# Pull latest code (if using git)
git pull origin main

# Redeploy
./deploy/deploy.sh
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs for errors
docker compose -f docker-compose.prod.yml logs

# Check if ports are already in use
sudo netstat -tlnp | grep -E ':(80|443|5432|6379)'

# Restart Docker
sudo systemctl restart docker
```

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Test renewal
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew --force-renewal
```

### Database Connection Errors

```bash
# Check database is running
docker compose -f docker-compose.prod.yml ps db

# Check database logs
docker compose -f docker-compose.prod.yml logs db

# Verify credentials in .env file
cat /opt/dcnetwork-api/.env | grep SQL_
```

### Permission Issues

```bash
# Fix media directory permissions
sudo chown -R 1000:1000 /opt/dcnetwork-api/media
sudo chmod -R 755 /opt/dcnetwork-api/media
```

### Cannot Access the API

1. Check firewall:
   ```bash
   sudo ufw status
   ```

2. Check if services are running:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

3. Check nginx configuration:
   ```bash
   docker compose -f docker-compose.prod.yml exec nginx nginx -t
   ```

4. Test from server:
   ```bash
   curl http://localhost/health/
   ```

## Security Checklist

Before going live, ensure:

- [ ] `DEBUG=0` in `.env`
- [ ] Strong `SECRET_KEY` is set
- [ ] Strong database password is set
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] `CSRF_TRUSTED_ORIGINS` includes your domain
- [ ] SSL certificate is installed and working
- [ ] Firewall (UFW) is enabled
- [ ] Backups are scheduled
- [ ] Superuser account is created
- [ ] Default passwords are changed

## Next Steps

1. Test all API endpoints
2. Configure monitoring (optional)
3. Set up error tracking (optional)
4. Review security settings
5. Document any custom configurations

## Getting Help

- Check logs: `docker compose -f docker-compose.prod.yml logs`
- Review documentation: `DEPLOYMENT.md`
- Check script documentation: `deploy/README.md`

