# Database Reset Guide

This guide explains how to reset your database in production after resetting your Django migrations.

## ⚠️ IMPORTANT WARNING

**Both scripts will DELETE ALL DATA in your database!** This includes:
- All user accounts
- All application data
- All migration history

Make sure you have backups if you need to preserve any data.

---

## When to Use Database Reset

Use these scripts when you have:
- Reset your Django migrations (deleted migration files and recreated them)
- Need to start with a fresh database
- Migration conflicts that cannot be resolved easily

---

## Option 1: Reset Database (Recommended)

**Script:** `reset-db-production.sh`

**What it does:**
- Stops application services (keeps database running)
- Drops the existing database
- Creates a fresh database
- Applies new migrations
- Restarts all services

**Advantages:**
- Faster (doesn't recreate Docker volume)
- Keeps database container configuration
- More precise control

**Usage:**
```bash
# Make executable (first time only)
chmod +x deploy/reset-db-production.sh

# Run the script
sudo ./deploy/reset-db-production.sh
```

**When to use:** When you just need to reset the database data and apply fresh migrations.

---

## Option 2: Reset Database Volume (Alternative)

**Script:** `reset-db-volume.sh`

**What it does:**
- Stops all services
- Removes the entire database Docker volume
- Creates a new volume
- Starts services and applies migrations

**Advantages:**
- Complete clean slate (removes everything)
- Useful when database structure is corrupted
- Ensures no leftover files or configurations

**Usage:**
```bash
# Make executable (first time only)
chmod +x deploy/reset-db-volume.sh

# Run the script
sudo ./deploy/reset-db-volume.sh
```

**When to use:** When Option 1 fails or when you want to completely remove the database volume.

---

## After Running Either Script

1. **Create a superuser:**
   ```bash
   docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser
   ```

2. **Verify migrations:**
   ```bash
   docker compose -f docker-compose.prod.yml exec api python manage.py showmigrations
   ```

3. **Check service status:**
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

4. **View logs (if needed):**
   ```bash
   docker compose -f docker-compose.prod.yml logs -f api
   ```

---

## Troubleshooting

### Script fails with "Database not ready"
- Wait a few more seconds and try again
- Check database container logs: `docker compose -f docker-compose.prod.yml logs db`

### Script fails with "Migrations failed"
- Check API logs: `docker compose -f docker-compose.prod.yml logs api`
- Verify migration files exist: `ls -la account/migrations/ travel/migrations/`
- Check for syntax errors in models or migrations

### Volume not found (Option 2)
- This is normal if the volume doesn't exist yet
- The script will create a new volume automatically

### Permission denied
- Make sure to run with `sudo` or as a user with Docker permissions
- Check script permissions: `ls -la deploy/reset-db-*.sh`

---

## Safety Features

Both scripts include:
- ✅ Explicit confirmation prompts (prevents accidental execution)
- ✅ Pre-flight checks (verifies .env file exists)
- ✅ Health checks (waits for services to be ready)
- ✅ Error handling (shows helpful error messages)
- ✅ Status reporting (shows what's happening at each step)

---

## Script Workflow

Both scripts follow this general workflow:

1. **Safety checks** - Verify environment and get confirmation
2. **Stop services** - Gracefully stop application services
3. **Reset database/volume** - Remove existing data
4. **Start database** - Ensure database is ready
5. **Start API** - Start API container for migrations
6. **Apply migrations** - Run Django migrations
7. **Collect static files** - Update static files
8. **Restart services** - Start all services
9. **Status report** - Show final status and next steps

---

## Need Help?

If you encounter issues:

1. Check the script output for error messages
2. Review container logs: `docker compose -f docker-compose.prod.yml logs`
3. Verify your `.env` file is configured correctly
4. Check that migration files exist and are valid
5. Ensure Docker and Docker Compose are working correctly

