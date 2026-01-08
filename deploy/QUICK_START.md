# Quick Start Guide

## 🚀 Fast Deployment (5 Steps)

### 1. Initial Setup (One-Time)
```bash
sudo ./deploy/setup.sh
```

### 2. Configure Environment
```bash
cp env.prod.example .env
nano .env  # Edit with your settings
```

### 3. Deploy
```bash
sudo ./deploy/deploy.sh
```

### 4. Create Admin User (Optional)
```bash
docker compose -f docker-compose.prod.yml exec api python manage.py createsuperuser
```

### 5. Setup SSL (After DNS is configured)
```bash
sudo ./deploy/ssl-setup.sh
```

Then update `.env`:
```bash
SECURE_SSL_REDIRECT=1
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1
```

Restart API:
```bash
docker compose -f docker-compose.prod.yml restart api
```

---

## 🔄 Updating Code

```bash
sudo ./deploy/update.sh
```

---

## 📊 Common Commands

```bash
# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart services
docker compose -f docker-compose.prod.yml restart

# Check resource usage
docker stats
free -h
```

---

## 🆘 Quick Troubleshooting

**Services won't start?**
```bash
docker compose -f docker-compose.prod.yml logs
```

**Out of memory?**
```bash
docker system prune -a
docker compose -f docker-compose.prod.yml restart
```

**SSL issues?**
```bash
sudo certbot certificates
docker compose -f docker-compose.prod.yml logs nginx
```

---

For detailed instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

