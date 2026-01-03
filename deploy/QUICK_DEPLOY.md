# Quick Deployment Guide

## One-Command Setup (After Initial Server Prep)

```bash
# 1. Initial server setup
sudo ./deploy/ubuntu-setup.sh

# 2. Configure .env file
cp env.prod.example .env
nano .env  # Edit with your settings

# 3. Setup SSL (after DNS is configured)
sudo ./deploy/ssl-setup.sh

# 4. Deploy application
./deploy/deploy.sh
```

## Environment Variables Checklist

Before deploying, ensure these are set in `.env`:

- [ ] `SECRET_KEY` - Generate with: `python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- [ ] `SQL_USER` - Database username
- [ ] `SQL_PASSWORD` - Strong database password
- [ ] `SQL_DATABASE` - Database name
- [ ] `ALLOWED_HOSTS` - Must include `api.goholiday.id`
- [ ] `CSRF_TRUSTED_ORIGINS` - Must include `https://api.goholiday.id`
- [ ] `CORS_ALLOWED_ORIGINS` - Your frontend domain(s)
- [ ] `MAILGUN_SMTP_LOGIN` - Mailgun credentials
- [ ] `MAILGUN_SMTP_PASSWORD` - Mailgun password
- [ ] `DEBUG=0` - Must be 0 in production

## Common Commands

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart services
docker compose -f docker-compose.prod.yml restart

# Create superuser
docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser

# Run backup
./deploy/backup.sh

# Update and redeploy
git pull
./deploy/deploy.sh
```

