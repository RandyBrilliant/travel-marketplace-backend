# Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- A `.env` file configured (see below)

## Step 1: Create `.env` file

Copy the example file and update with your values:

```bash
cp env.example .env
```

## Step 2: Update `.env` file

**Minimum required changes:**

```bash
# Database (required)
SQL_DATABASE=travel_marketplace
SQL_USER=postgres
SQL_PASSWORD=your-secure-password
SECRET_KEY=your-secret-key-here  # Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Email (optional for testing - can use console backend)
MAILGUN_SMTP_LOGIN=your-mailgun-login
MAILGUN_SMTP_PASSWORD=your-mailgun-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

**For testing without Mailgun**, you can use console email backend (emails print to console):

Add to `backend/settings.py` temporarily:
```python
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## Step 3: Start all services

```bash
docker-compose up -d
```

This will start:
- ✅ API server (port 8000)
- ✅ PostgreSQL database (port 5432)
- ✅ Redis (port 6379)
- ✅ Celery worker (email processing)
- ✅ Celery beat (scheduled tasks)

## Step 4: Check services are running

```bash
# View all services
docker-compose ps

# View logs
docker-compose logs -f

# Check specific service
docker-compose logs -f api
docker-compose logs -f celery
```

## Step 5: Create superuser (optional)

```bash
docker-compose exec api python manage.py createsuperuser
```

Or use the custom command:
```bash
docker-compose exec api python manage.py createsuperadmin --email admin@example.com --password yourpassword --name "Admin User"
```

## Step 6: Access the API

- **API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/api/docs (if configured)

## Troubleshooting

### Services won't start

1. **Check `.env` file exists:**
   ```bash
   ls -la .env
   ```

2. **Check database credentials:**
   Make sure `SQL_USER`, `SQL_PASSWORD`, and `SQL_DATABASE` are set in `.env`

3. **Check ports are available:**
   ```bash
   # Check if ports are in use
   lsof -i :8000  # API
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   ```

### Celery worker not processing tasks

1. **Check Redis is running:**
   ```bash
   docker-compose exec redis redis-cli ping
   # Should return: PONG
   ```

2. **Check Celery logs:**
   ```bash
   docker-compose logs celery
   ```

3. **Verify environment variables:**
   ```bash
   docker-compose exec celery env | grep CELERY
   ```

### Database connection errors

1. **Wait for database to be ready:**
   The services have health checks, but if issues persist:
   ```bash
   docker-compose logs db
   ```

2. **Check migrations ran:**
   ```bash
   docker-compose exec api python manage.py showmigrations
   ```

### Email not sending

1. **For testing, use console backend** (see Step 2)
2. **Check Mailgun credentials** in `.env`
3. **Check Celery worker logs:**
   ```bash
   docker-compose logs celery | grep -i error
   ```

## Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a specific service
docker-compose restart celery

# View logs
docker-compose logs -f [service-name]

# Run Django commands
docker-compose exec api python manage.py [command]

# Access database
docker-compose exec db psql -U $SQL_USER -d $SQL_DATABASE

# Access Redis CLI
docker-compose exec redis redis-cli

# Rebuild after code changes
docker-compose up -d --build

# Clean everything (removes volumes!)
docker-compose down -v
```

## What's Running?

After `docker-compose up -d`, you should see:

```
✅ api          - Django API server
✅ db           - PostgreSQL database  
✅ redis        - Redis message broker
✅ celery       - Email worker
✅ celery-beat  - Scheduled tasks
```

All services will automatically:
- ✅ Run database migrations
- ✅ Collect static files
- ✅ Connect to each other
- ✅ Restart on failure

## Next Steps

1. **Set up Mailgun** (or use console backend for testing)
2. **Create your first user** via API or admin
3. **Test email sending** by triggering a welcome email
4. **Configure frontend** to connect to `http://localhost:8000`

## Production Deployment

For production, you'll need to:
- Use environment-specific `.env` files
- Set up proper SSL certificates
- Configure production database
- Set up monitoring and logging
- Use production Mailgun domain
- Configure proper CORS settings

