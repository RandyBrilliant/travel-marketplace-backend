## Backend Docker Quickstart

1. **Copy environment file:**
   ```bash
   cp env.example .env
   ```

2. **Update `.env` with your settings** (minimum: `SECRET_KEY`, `SQL_USER`, `SQL_PASSWORD`)

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Create superuser:**
   ```bash
   docker-compose exec api python manage.py createsuperadmin
   ```

5. **Access the API:**
   - API: http://localhost:8000
   - Admin: http://localhost:8000/admin

**Services included:**
- ✅ API server (Django)
- ✅ PostgreSQL database
- ✅ Redis (for Celery)
- ✅ Celery worker (email processing)
- ✅ Celery beat (scheduled tasks)

**See `QUICK_START.md` for detailed setup instructions.**

