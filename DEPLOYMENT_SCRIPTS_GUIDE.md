# Deployment Scripts Guide

This guide explains when to use each deployment script.

## 📋 Available Scripts

### 0. `deploy/fix-2gb-memory.sh` - 2GB RAM Optimization ⚠️

**When to use:**
- Running on a 2GB RAM server (DigitalOcean Basic droplet)
- Containers being killed with OOM errors (exit code 137)
- Celery-beat keeps restarting

**What it does:**
- Fixes Redis memory overcommit warning
- Installs memory-optimized docker-compose configuration
- Reduces workers and memory limits
- Total memory: 980MB → 850MB

**Usage:**
```bash
cd ~/travel-marketplace-backend
sudo ./deploy/fix-2gb-memory.sh
```

**Time:** ~2-3 minutes  
**Downtime:** ~1 minute  
**Data loss:** None ✅

See [2GB-RAM-GUIDE.md](deploy/2GB-RAM-GUIDE.md) for details.

---

### 1. `deploy/update.sh` ⭐ **USE THIS FOR REGULAR UPDATES**

**When to use:**
- You made code changes to views, models, serializers, etc.
- You added new features
- You fixed bugs
- You updated dependencies

**What it does:**
- Pulls latest code (if using git)
- Rebuilds Docker images (only changed layers)
- Restarts containers
- Runs database migrations
- Collects static files

**Usage:**
```bash
cd ~/travel-marketplace-backend
./deploy/update.sh
```

**Time:** ~2-3 minutes  
**Downtime:** ~30 seconds  
**Data loss:** None ✅

---

### 2. `deploy/deploy.sh` - Full Deployment

**When to use:**
- First time deployment
- Major infrastructure changes
- Need to rebuild everything from scratch (but keep database)

**What it does:**
- Everything in update.sh
- Plus: copies files, sets permissions, more thorough checks

**Usage:**
```bash
cd ~/travel-marketplace-backend
sudo ./deploy/deploy.sh
```

**Time:** ~5-10 minutes  
**Downtime:** ~1 minute  
**Data loss:** None ✅

---

### 3. `deploy/fresh-start.sh` - Automated Fresh Start

**When to use:**
- After running complete-reset.sh
- First time setup on new server
- Want automated checks and deployment

**What it does:**
- Checks .env file
- Verifies configuration
- Runs full deployment
- Performs health checks

**Usage:**
```bash
cd ~/travel-marketplace-backend
sudo ./deploy/fresh-start.sh
```

**Time:** ~5-10 minutes  
**Downtime:** All services down until complete  
**Data loss:** None (but assumes clean state) ✅

---

### 4. `deploy/complete-reset.sh` ⚠️ **NUCLEAR OPTION**

**When to use:**
- Everything is broken and you need to start over
- Testing clean deployment
- Major version upgrades
- Database needs complete reset

**What it does:**
- Stops ALL containers
- Removes ALL containers
- Removes ALL volumes
- Removes ALL images
- Cleans Docker system
- **DELETES DATABASE** ❌

**Usage:**
```bash
cd ~/travel-marketplace-backend
sudo ./deploy/complete-reset.sh
```

**Time:** ~2-3 minutes  
**Downtime:** Everything deleted  
**Data loss:** **YES - ALL DATA DELETED** ❌

---

### 5. `deploy/backup.sh` - Backup Database & Media

**When to use:**
- Before major updates
- Before complete-reset
- Regular scheduled backups (daily via cron)

**What it does:**
- Backs up PostgreSQL database
- Backs up media files
- Creates timestamped backup folder

**Usage:**
```bash
cd ~/travel-marketplace-backend
./deploy/backup.sh
```

**Time:** ~1-5 minutes (depends on data size)

---

## 🔄 Common Workflows

### Regular Code Update (Most Common)

```bash
# On your local machine - make changes and commit
git add .
git commit -m "Fixed user authentication"
git push origin main

# On server
cd ~/travel-marketplace-backend
git pull
./deploy/update.sh
```

### Major Update with Backup

```bash
cd ~/travel-marketplace-backend

# 1. Backup first
./deploy/backup.sh

# 2. Pull changes
git pull

# 3. Update
./deploy/update.sh

# 4. Check logs
docker compose -f docker-compose.prod.yml logs -f
```

### Complete Fresh Start

```bash
cd ~/travel-marketplace-backend

# 1. Backup database (if you want to keep data)
./deploy/backup.sh

# 2. Complete reset
sudo ./deploy/complete-reset.sh

# 3. Configure .env
nano .env

# 4. Fresh deployment
sudo ./deploy/fresh-start.sh

# 5. Create superuser
docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser
```

### Quick Restart (No Code Changes)

```bash
cd ~/travel-marketplace-backend

# Just restart services
docker compose -f docker-compose.prod.yml restart

# Or restart specific service
docker compose -f docker-compose.prod.yml restart api
docker compose -f docker-compose.prod.yml restart nginx
```

---

## 📊 Script Comparison

| Script | Use Case | Time | Downtime | Data Loss | Requires sudo |
|--------|----------|------|----------|-----------|---------------|
| `update.sh` | Regular updates | 2-3 min | 30s | No | No* |
| `deploy.sh` | Full deployment | 5-10 min | 1 min | No | Yes |
| `fresh-start.sh` | Automated setup | 5-10 min | Full | No | Yes |
| `complete-reset.sh` | Nuclear reset | 2-3 min | Full | **YES** | Yes |
| `backup.sh` | Backup only | 1-5 min | None | No | No* |

*May require sudo depending on file permissions

---

## 🎯 Quick Decision Tree

**Did you just make code changes?**  
→ Use `update.sh`

**Is this your first deployment?**  
→ Use `fresh-start.sh`

**Is everything broken?**  
→ Use `complete-reset.sh` then `fresh-start.sh`

**Just need to restart?**  
→ Use `docker compose restart`

**Want to be safe before updating?**  
→ Run `backup.sh` first

---

## 💡 Pro Tips

1. **Always backup before major changes:**
   ```bash
   ./deploy/backup.sh && ./deploy/update.sh
   ```

2. **View logs during deployment:**
   ```bash
   # In another terminal
   docker compose -f docker-compose.prod.yml logs -f
   ```

3. **Check what changed before deploying:**
   ```bash
   git pull --dry-run
   git diff origin/main
   ```

4. **Rollback if something goes wrong:**
   ```bash
   git reset --hard HEAD~1
   ./deploy/update.sh
   ```

5. **Schedule daily backups (add to crontab):**
   ```bash
   crontab -e
   # Add: 0 2 * * * /path/to/deploy/backup.sh
   ```

---

## 🚨 Important Notes

- `update.sh` is **safe** and can be run anytime
- `complete-reset.sh` **deletes everything** - use with caution!
- Always check `.env` file has `SECURE_SSL_REDIRECT=false`
- Database backups are stored in `backups/` directory
- Keep at least 3 recent backups before deleting old ones

---

## 📞 Need Help?

If something goes wrong:

```bash
# Check container status
docker compose -f docker-compose.prod.yml ps

# View all logs
docker compose -f docker-compose.prod.yml logs

# View specific service logs
docker compose -f docker-compose.prod.yml logs api
docker compose -f docker-compose.prod.yml logs nginx
docker compose -f docker-compose.prod.yml logs celery

# Check if API is responding
curl http://localhost/health/
curl https://api.goholiday.id/health/
```

