# Production Update Guide

Complete guide for updating your backend in production with minimal or zero downtime.

## 🎯 Update Strategies Overview

### Strategy 1: Quick Update (Simple, ~30 seconds downtime)
**When to use:** Small changes, low traffic, or maintenance windows

```bash
sudo ./deploy/update.sh
```

**Downtime:** ~30-60 seconds  
**Risk:** Low  
**Complexity:** Simple

### Strategy 2: Rolling Update (Near-zero downtime)
**When to use:** Production with active users, code changes only

```bash
sudo ./deploy/rolling-update.sh  # We'll create this
```

**Downtime:** Minimal (<5 seconds)  
**Risk:** Low  
**Complexity:** Medium

### Strategy 3: Hot Reload (Zero downtime, code changes only)
**When to use:** Minor code changes, no DB migrations

```bash
docker compose restart api celery
```

**Downtime:** None  
**Risk:** Medium (if breaking changes)  
**Complexity:** Simple

### Strategy 4: Blue-Green Deployment (Zero downtime, advanced)
**When to use:** Major updates, schema changes, high-traffic production

**Downtime:** None  
**Risk:** Low  
**Complexity:** Advanced

---

## 📋 Detailed Update Strategies

### Strategy 1: Quick Update (Current `update.sh`)

**What it does:**
1. Pulls latest code (optional)
2. **Stops ALL containers** ⚠️ (causes downtime)
3. Rebuilds images
4. Starts services
5. Runs migrations
6. Collects static files

**Usage:**

```bash
cd /home/regretzz/travel-marketplace-backend

# Quick update with downtime
sudo ./deploy/update.sh

# Or with alias (if configured)
tm-update
```

**Pros:**
- ✅ Simple and reliable
- ✅ Clean state after update
- ✅ Works for all types of changes

**Cons:**
- ❌ ~30-60 seconds downtime
- ❌ All users disconnected
- ❌ Ongoing requests fail

**Best for:**
- Development/staging environments
- Scheduled maintenance windows
- Low-traffic periods (late night)
- Breaking database changes

---

### Strategy 2: Rolling Update (Minimal Downtime)

This strategy updates services one by one, keeping at least one instance running.

**Create this script:**

```bash
nano /home/regretzz/travel-marketplace-backend/deploy/rolling-update.sh
```

**Script content:** (see below)

**Usage:**

```bash
cd /home/regretzz/travel-marketplace-backend
sudo ./deploy/rolling-update.sh
```

**Pros:**
- ✅ Minimal downtime (<5 seconds)
- ✅ Most users unaffected
- ✅ Can rollback easily

**Cons:**
- ❌ Not suitable for breaking DB changes
- ❌ Requires careful migration planning
- ❌ More complex

**Best for:**
- Production with active users
- Code changes only
- Compatible migrations
- Bug fixes and features

---

### Strategy 3: Hot Reload (Zero Downtime)

For **code-only changes** without DB migrations:

```bash
# Just restart the API service
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml restart api

# If you changed background tasks
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml restart celery

# Monitor
docker compose -f /home/regretzz/travel-marketplace-backend/docker-compose.prod.yml logs -f api
```

**When to use:**
- ✅ View changes
- ✅ Minor bug fixes
- ✅ Configuration changes
- ✅ Utility functions
- ❌ Database migrations
- ❌ Model changes
- ❌ Dependency updates

**Downtime:** None (Nginx buffers requests during restart)

---

## 🔄 Rolling Update Script (Recommended for Production)

Create `/home/regretzz/travel-marketplace-backend/deploy/rolling-update.sh`:

```bash
#!/bin/bash

# Rolling Update Script - Minimal Downtime
# This updates services one by one while keeping others running

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=========================================="
echo "Rolling Update - Minimal Downtime"
echo "==========================================${NC}"
echo ""

cd "$APP_DIR" || exit 1

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run with sudo${NC}"
    exit 1
fi

# Step 1: Pull latest code
echo -e "${YELLOW}[1/8] Updating code...${NC}"
if [ -d ".git" ]; then
    git pull
    echo -e "${GREEN}✓ Code updated${NC}"
else
    echo -e "${YELLOW}Not a git repo, skipping${NC}"
fi

# Step 2: Build new images (doesn't affect running containers)
echo -e "${YELLOW}[2/8] Building new images...${NC}"
docker compose -f docker-compose.prod.yml build
echo -e "${GREEN}✓ Images built${NC}"

# Step 3: Run migrations (safe to run while services are up)
echo -e "${YELLOW}[3/8] Running database migrations...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput || \
    docker compose -f docker-compose.prod.yml run --rm api python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations complete${NC}"

# Step 4: Update Celery Beat (low priority, can have downtime)
echo -e "${YELLOW}[4/8] Updating Celery Beat...${NC}"
docker compose -f docker-compose.prod.yml stop celery-beat
docker compose -f docker-compose.prod.yml rm -f celery-beat
docker compose -f docker-compose.prod.yml up -d celery-beat
echo -e "${GREEN}✓ Celery Beat updated${NC}"
sleep 3

# Step 5: Update Celery Worker (background tasks)
echo -e "${YELLOW}[5/8] Updating Celery Worker...${NC}"
docker compose -f docker-compose.prod.yml stop celery
docker compose -f docker-compose.prod.yml rm -f celery
docker compose -f docker-compose.prod.yml up -d celery
echo -e "${GREEN}✓ Celery Worker updated${NC}"
sleep 3

# Step 6: Update API (main service - quick restart)
echo -e "${YELLOW}[6/8] Updating API service...${NC}"
echo -e "${BLUE}This will cause ~2-5 seconds of request buffering${NC}"
docker compose -f docker-compose.prod.yml stop api
docker compose -f docker-compose.prod.yml rm -f api
docker compose -f docker-compose.prod.yml up -d api
echo -e "${GREEN}✓ API service updated${NC}"

# Step 7: Wait for health check
echo -e "${YELLOW}[7/8] Waiting for services to be healthy...${NC}"
sleep 10

# Test health
for i in {1..12}; do
    if curl -f -s http://localhost/health/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is healthy!${NC}"
        break
    else
        if [ $i -eq 12 ]; then
            echo -e "${RED}✗ API health check failed${NC}"
            echo "Check logs: docker compose -f docker-compose.prod.yml logs -f api"
            exit 1
        fi
        echo "Waiting... ($i/12)"
        sleep 5
    fi
done

# Step 8: Collect static files
echo -e "${YELLOW}[8/8] Collecting static files...${NC}"
docker compose -f docker-compose.prod.yml exec -T api python manage.py collectstatic --noinput --clear || true
echo -e "${GREEN}✓ Static files collected${NC}"

# Restart nginx to pick up any static file changes
echo -e "${YELLOW}Restarting Nginx...${NC}"
docker compose -f docker-compose.prod.yml restart nginx
sleep 2

echo ""
echo -e "${GREEN}=========================================="
echo "Rolling Update Complete!"
echo "==========================================${NC}"
echo ""

echo "Container Status:"
docker compose -f docker-compose.prod.yml ps
echo ""

echo -e "${GREEN}✓ Update completed with minimal downtime${NC}"
echo ""
echo -e "${BLUE}Monitor logs:${NC}"
echo "docker compose -f docker-compose.prod.yml logs -f api"
echo ""
```

Make it executable:
```bash
chmod +x /home/regretzz/travel-marketplace-backend/deploy/rolling-update.sh
```

---

## 🎨 Update Workflow by Change Type

### 1. **Code Changes Only** (Views, Serializers, Utils)

**No database migrations, no new dependencies**

```bash
# Option A: Hot reload (fastest)
docker compose restart api celery

# Option B: Rolling update (safest)
sudo ./deploy/rolling-update.sh
```

**Downtime:** None to minimal

---

### 2. **Code + Compatible Migrations**

**Migrations that don't break existing code** (adding fields with defaults, new tables)

```bash
# Rolling update handles this
sudo ./deploy/rolling-update.sh
```

**Steps:**
1. Build new images
2. Run migrations (safe with old code)
3. Update services with new code

**Downtime:** Minimal (~5 seconds)

---

### 3. **Breaking Database Changes**

**Migrations that require code changes** (removing fields, renaming columns)

```bash
# Use quick update with downtime
sudo ./deploy/update.sh
```

**Steps:**
1. Schedule maintenance window
2. Notify users
3. Stop all services
4. Run migrations
5. Update code
6. Start services

**Downtime:** 30-60 seconds (unavoidable)

---

### 4. **Dependency Updates** (requirements.txt)

```bash
# Full rebuild required
sudo ./deploy/update.sh
```

Or for minimal downtime:

```bash
# Build new images
docker compose -f docker-compose.prod.yml build --no-cache

# Rolling update
sudo ./deploy/rolling-update.sh
```

---

### 5. **Configuration Changes** (.env, settings)

```bash
# If no code rebuild needed
docker compose restart api celery celery-beat

# If settings.py changed
sudo ./deploy/rolling-update.sh
```

---

### 6. **Static Files Only** (CSS, JS)

```bash
# Just collect static files
docker compose exec api python manage.py collectstatic --noinput --clear
docker compose restart nginx
```

**Downtime:** None

---

## 🚀 Recommended Update Process

### Step-by-Step Production Update

**1. Test Locally First**

```bash
# On your local machine
python manage.py test
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
```

**2. Backup Database**

```bash
# Before any update
sudo ./deploy/backup.sh

# Or manual backup
docker compose exec -T db pg_dump -U travel_user travel_marketplace > backup-before-update.sql
```

**3. Choose Update Strategy**

Based on your changes:
- Code only → Rolling update
- Code + compatible migrations → Rolling update
- Breaking changes → Quick update (scheduled downtime)
- Hot fix → Hot reload

**4. Perform Update**

```bash
# Most common: Rolling update
sudo ./deploy/rolling-update.sh

# Or quick update
sudo ./deploy/update.sh
```

**5. Verify**

```bash
# Check health
curl https://api.goholiday.id/health/

# Check logs
docker compose logs -f api

# Monitor resources
docker stats

# Test key endpoints
curl https://api.goholiday.id/api/tours/
```

**6. Monitor**

Watch for 10-15 minutes after update:
- Error rates
- Response times
- Memory usage
- Database connections

---

## 🔧 Advanced: Blue-Green Deployment (Zero Downtime)

For mission-critical updates, use blue-green deployment:

### Setup

1. **Run two complete stacks** (blue and green)
2. **Load balancer** switches traffic
3. **Zero downtime** during switch

### Implementation (Advanced)

```bash
# This requires two separate docker-compose files
# and a load balancer (Nginx or cloud LB)

# Start green environment (new version)
docker compose -f docker-compose.green.yml up -d

# Wait for health check
curl http://localhost:8001/health/

# Switch Nginx upstream to green
# Edit nginx config, reload

# Stop blue environment (old version)
docker compose -f docker-compose.blue.yml down
```

**For 2GB server:** Not recommended due to resource constraints

---

## 📊 Update Comparison

| Strategy | Downtime | Complexity | DB Changes | Dependencies |
|----------|----------|------------|------------|--------------|
| Quick Update | 30-60s | Low | ✅ All | ✅ Yes |
| Rolling Update | <5s | Medium | ⚠️ Compatible only | ✅ Yes |
| Hot Reload | 0s | Low | ❌ No | ❌ No |
| Blue-Green | 0s | High | ✅ All | ✅ Yes |

---

## ✅ Best Practices

### 1. **Always Backup First**

```bash
sudo ./deploy/backup.sh
```

### 2. **Test Migrations Locally**

```bash
# Check for migration issues
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
```

### 3. **Use Compatible Migrations**

**Good** (can run before code update):
```python
# Adding field with default
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='tour',
            name='rating',
            field=models.IntegerField(default=0),
        ),
    ]
```

**Bad** (requires code update first):
```python
# Removing field - breaks old code
class Migration(migrations.Migration):
    operations = [
        migrations.RemoveField(
            model_name='tour',
            name='old_field',
        ),
    ]
```

### 4. **Monitor After Update**

```bash
# Watch logs
docker compose logs -f api

# Monitor resources
watch -n 1 docker stats

# Check error logs
tail -f /home/regretzz/travel-marketplace-backend/logs/django.log
```

### 5. **Have a Rollback Plan**

```bash
# Quick rollback (if using git)
git log --oneline -5  # Find previous commit
git reset --hard <previous-commit>
sudo ./deploy/update.sh

# Or restore from backup
docker compose exec -T db psql -U travel_user travel_marketplace < backup-before-update.sql
```

---

## 🛠️ Quick Reference

### Add Aliases to Your Shell

```bash
# Add to ~/.bashrc
alias tm-update='cd $APP_DIR && sudo ./deploy/rolling-update.sh'
alias tm-quick-update='cd $APP_DIR && sudo ./deploy/update.sh'
alias tm-reload='docker compose -f $APP_DIR/docker-compose.prod.yml restart api celery'
alias tm-backup-before-update='cd $APP_DIR && sudo ./deploy/backup.sh'
```

### Common Update Commands

```bash
# Most common: Rolling update
tm-update

# Hot reload (code only, no migrations)
tm-reload

# Backup before update
tm-backup-before-update

# Full update with downtime
tm-quick-update

# Just collect static files
docker compose exec api python manage.py collectstatic --noinput --clear

# Check migration status
docker compose exec api python manage.py showmigrations

# View recent logs
docker compose logs --tail=100 -f api
```

---

## 🎯 Decision Tree

```
Need to update?
│
├─ Just code changes (no migrations)?
│  ├─ Yes → Use hot reload: docker compose restart api
│  └─ No → Continue
│
├─ Database migrations needed?
│  ├─ Yes → Are they compatible with old code?
│  │  ├─ Yes → Use rolling update: sudo ./deploy/rolling-update.sh
│  │  └─ No → Use quick update: sudo ./deploy/update.sh (scheduled downtime)
│  └─ No → Use rolling update
│
├─ Dependency changes?
│  └─ Yes → Use rolling update (with --no-cache build)
│
└─ Static files only?
   └─ Yes → collectstatic + nginx restart (no downtime)
```

---

## 📝 Summary

**For most production updates:**
```bash
# 1. Backup
sudo ./deploy/backup.sh

# 2. Update (minimal downtime)
sudo ./deploy/rolling-update.sh

# 3. Monitor
docker compose logs -f api
```

**For emergency hot fixes:**
```bash
docker compose restart api celery
```

**For breaking changes:**
```bash
# Schedule maintenance window
sudo ./deploy/update.sh
```

---

**Your current `update.sh` works great for scheduled maintenance!** 

For zero-downtime updates, create the `rolling-update.sh` script above. 🚀

