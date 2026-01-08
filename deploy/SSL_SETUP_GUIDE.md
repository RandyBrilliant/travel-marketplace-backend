# SSL Setup Guide for Rebuild (2GB/1vCPU Server)

Complete guide for setting up SSL certificates on your rebuilt server with optimized Nginx configuration.

## Overview

Your current setup has:
- ✅ Full SSL configuration ready (`api.goholiday.id.conf`)
- ✅ HTTP-only config for initial deployment (`api.goholiday.id.http-only.conf`)
- ✅ Automated SSL setup script (`ssl-setup.sh`)
- ✅ Optimized for 2GB RAM with rate limiting and security headers

## 🚀 Quick SSL Setup (For Rebuild)

### Step 1: Deploy Without SSL First

```bash
# Ensure you're using HTTP-only config initially
cd /opt/travel-marketplace-backend

# Make sure docker-compose.prod.yml uses the HTTP-only config
# The deploy script should handle this automatically

# Deploy
sudo ./deploy/deploy.sh
```

**Why HTTP first?**
- SSL certificates need HTTP (port 80) for validation
- Easier to troubleshoot initial deployment
- Can switch to SSL once everything works

### Step 2: Verify HTTP Deployment

```bash
# Test the API (replace with your server IP)
curl http://YOUR_SERVER_IP/health/

# Should return: {"status":"healthy"}

# Check DNS
dig +short api.goholiday.id

# Should return your server IP
```

### Step 3: Run SSL Setup Script

```bash
# Set your email for SSL notifications
export SSL_EMAIL=your-email@goholiday.id

# Run SSL setup (requires domain DNS to be configured)
sudo ./deploy/ssl-setup.sh
```

**What this does:**
- ✓ Validates DNS configuration
- ✓ Stops nginx temporarily
- ✓ Requests Let's Encrypt certificate
- ✓ Copies certificates to nginx/ssl/
- ✓ Sets up auto-renewal (cron job)
- ✓ Restarts nginx

### Step 4: Switch to SSL Configuration

The SSL configuration is optimized for your 2GB server. Here's what to verify:

```bash
# Check docker-compose.prod.yml
cat docker-compose.prod.yml | grep api.goholiday.id.conf

# Should show: ./nginx/api.goholiday.id.conf:/etc/nginx/conf.d/api.goholiday.id.conf:ro
```

### Step 5: Update Environment Variables

```bash
# Edit .env file
nano /opt/travel-marketplace-backend/.env

# Update these settings:
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

### Step 6: Restart Services

```bash
# Restart all services to apply SSL config
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml restart

# Wait for health check
sleep 10

# Test HTTPS
curl https://api.goholiday.id/health/
```

## 📋 Optimized Nginx Configuration Details

Your `api.goholiday.id.conf` is already optimized for 2GB RAM:

### Key Optimizations

#### 1. **Upstream Configuration with Keepalive**
```nginx
upstream api_backend {
    server api:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;              # Reuse connections
    keepalive_timeout 60s;
    keepalive_requests 100;
}
```
**Benefits:** Reduces connection overhead, better performance on low resources

#### 2. **HTTP to HTTPS Redirect**
```nginx
server {
    listen 80;
    server_name api.goholiday.id;
    
    # Allow SSL certificate validation
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect everything else to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}
```

#### 3. **SSL Security Settings (A+ Rating)**
```nginx
# Modern SSL protocols only
ssl_protocols TLSv1.2 TLSv1.3;

# Strong cipher suites
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256...';
ssl_prefer_server_ciphers off;

# Session caching (reduced for low memory)
ssl_session_cache shared:SSL:10m;    # 10MB cache
ssl_session_timeout 10m;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
```

#### 4. **Security Headers**
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

#### 5. **Rate Limiting (Protection)**
In `nginx.conf`:
```nginx
# API rate limiting: 10 requests/second
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Login rate limiting: 5 requests/minute
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
```

Applied in site config:
```nginx
# API endpoints
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    # ... proxy settings
}

# Login endpoints (stricter)
location ~ ^/api/(v1/)?(account|auth)/.*/(login|register)/ {
    limit_req zone=login_limit burst=3 nodelay;
    # ... proxy settings
}
```

#### 6. **Optimized Timeouts (for 2GB)**
```nginx
proxy_connect_timeout 10s;     # Connection to backend
proxy_send_timeout 90s;        # Sending request to backend
proxy_read_timeout 90s;        # Reading response from backend
```

#### 7. **Retry Logic (High Availability)**
```nginx
# Retry on errors
proxy_next_upstream error timeout http_502 http_503 http_504;
proxy_next_upstream_tries 2;
proxy_next_upstream_timeout 5s;
```

#### 8. **Proxy Buffering (Memory Efficient)**
```nginx
proxy_buffering on;
proxy_buffer_size 4k;           # Small buffers for low RAM
proxy_buffers 8 4k;             # 8 buffers × 4KB = 32KB total
proxy_busy_buffers_size 8k;
```

## 🔧 Configuration File Management

### For Fresh Rebuild (Recommended Flow)

#### Option A: Start with HTTP, then SSL (Safest)

1. **Initial deployment** - Use HTTP-only config in `docker-compose.prod.yml`:
   ```yaml
   nginx:
     volumes:
       - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
       - ./nginx/api.goholiday.id.http-only.conf:/etc/nginx/conf.d/api.goholiday.id.conf:ro
   ```

2. **After SSL setup** - Switch to SSL config:
   ```yaml
   nginx:
     volumes:
       - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
       - ./nginx/api.goholiday.id.conf:/etc/nginx/conf.d/api.goholiday.id.conf:ro
       - ./nginx/ssl:/etc/nginx/ssl:ro  # Add SSL certificates
   ```

3. Restart: `docker compose restart nginx`

#### Option B: Use SSL from Start (If certificates exist)

If you have existing SSL certificates from backup:

1. Copy certificates to `nginx/ssl/api.goholiday.id/`:
   ```bash
   mkdir -p nginx/ssl/api.goholiday.id
   cp /path/to/backup/fullchain.pem nginx/ssl/api.goholiday.id/
   cp /path/to/backup/privkey.pem nginx/ssl/api.goholiday.id/
   cp /path/to/backup/chain.pem nginx/ssl/api.goholiday.id/
   chmod 644 nginx/ssl/api.goholiday.id/fullchain.pem
   chmod 600 nginx/ssl/api.goholiday.id/privkey.pem
   chmod 644 nginx/ssl/api.goholiday.id/chain.pem
   ```

2. Deploy with SSL config from the start

## 🔐 SSL Certificate Management

### Auto-Renewal (Already Configured)

The SSL setup script creates a cron job:
```bash
# Check current cron
crontab -l | grep certbot

# Should show:
0 3 * * * certbot renew --quiet --deploy-hook '/etc/letsencrypt/renewal-hooks/deploy/travel-api-nginx.sh'
```

### Manual Renewal (If Needed)

```bash
# Test renewal (dry run)
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal

# After renewal, restart nginx
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml restart nginx
```

### Check Certificate Status

```bash
# Check expiry
sudo certbot certificates

# Test SSL configuration
curl -vI https://api.goholiday.id 2>&1 | grep -i 'ssl\|tls\|cert'

# Online SSL test
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=api.goholiday.id
```

## 🛡️ Security Checklist

After SSL setup, verify these security measures:

### 1. SSL Configuration
- [ ] HTTPS working: `curl -I https://api.goholiday.id`
- [ ] HTTP redirects to HTTPS
- [ ] Certificate valid and trusted
- [ ] No mixed content warnings
- [ ] SSL Labs test shows A+ rating

### 2. Security Headers
```bash
# Check security headers
curl -I https://api.goholiday.id/health/

# Should include:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
```

### 3. Rate Limiting
```bash
# Test API rate limiting (should fail after 10/sec)
for i in {1..15}; do curl https://api.goholiday.id/api/tours/; done

# Should see 429 (Too Many Requests) after burst
```

### 4. Django Security Settings
In `.env`:
```bash
DEBUG=0                          # MUST be 0 in production
SECURE_SSL_REDIRECT=true         # After SSL is configured
SESSION_COOKIE_SECURE=true       # Secure cookies only via HTTPS
CSRF_COOKIE_SECURE=true          # CSRF cookies only via HTTPS
```

## 📊 Performance Tuning for 2GB

### Nginx Worker Configuration

In `nginx.conf`:
```nginx
worker_processes 1;              # Match single vCPU
worker_connections 1024;         # Reduced from 2048 for low RAM
worker_rlimit_nofile 8192;       # File descriptor limit
```

### Connection Management
```nginx
keepalive_timeout 30;            # Reduced from 65 (save memory)
keepalive_requests 100;          # Requests per connection
reset_timedout_connection on;    # Clean up timed out connections
```

### Buffer Sizes (Memory Optimized)
```nginx
client_body_buffer_size 128k;    # POST data buffer
client_max_body_size 20M;        # Max upload size
client_header_buffer_size 1k;
large_client_header_buffers 4 8k;
```

## 🧪 Testing SSL Configuration

### 1. Basic Connectivity
```bash
# Health check
curl https://api.goholiday.id/health/
# Should return: {"status":"healthy"}

# API endpoint
curl https://api.goholiday.id/api/tours/
# Should return tour data or auth error
```

### 2. SSL Certificate Details
```bash
# View certificate
echo | openssl s_client -connect api.goholiday.id:443 -servername api.goholiday.id 2>/dev/null | openssl x509 -noout -dates

# Should show:
# notBefore=...
# notAfter=... (90 days from issue)
```

### 3. SSL Protocol Test
```bash
# Test TLS 1.2
openssl s_client -connect api.goholiday.id:443 -tls1_2 -servername api.goholiday.id

# Test TLS 1.3
openssl s_client -connect api.goholiday.id:443 -tls1_3 -servername api.goholiday.id

# Both should succeed
```

### 4. HSTS Header
```bash
# Check HSTS
curl -I https://api.goholiday.id | grep -i strict-transport-security

# Should return:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

### 5. OCSP Stapling
```bash
# Test OCSP stapling
echo QUIT | openssl s_client -connect api.goholiday.id:443 -status 2>/dev/null | grep -A 17 'OCSP response:'

# Should show OCSP response data
```

## 🐛 Troubleshooting

### Issue: "Certificate not found"

```bash
# Check if certificates exist
ls -la /opt/travel-marketplace-backend/nginx/ssl/api.goholiday.id/

# Should show:
# fullchain.pem
# privkey.pem
# chain.pem

# If missing, run SSL setup again
sudo ./deploy/ssl-setup.sh
```

### Issue: "Too many redirects"

**Cause:** SSL redirect loop when Django and Nginx both redirect

**Solution:** In `.env`, initially set:
```bash
SECURE_SSL_REDIRECT=false  # Let Nginx handle redirects
```

Only set to `true` if you want Django to also enforce SSL.

### Issue: "Connection refused on port 80"

```bash
# Check if nginx container is running
docker compose ps nginx

# Check nginx logs
docker compose logs nginx

# Common causes:
# - Port 80 already in use
# - Firewall blocking port 80
# - Nginx config error
```

### Issue: SSL certificate renewal fails

```bash
# Test renewal
sudo certbot renew --dry-run

# Common issues:
# - Port 80 not accessible from internet
# - Nginx not serving .well-known/acme-challenge/
# - Domain DNS changed

# Manual fix:
sudo ./deploy/ssl-setup.sh
```

### Issue: "Mixed content" warnings

**Cause:** Frontend loading HTTP resources on HTTPS page

**Solution:** Update frontend `.env`:
```bash
NEXT_PUBLIC_API_BASE_URL=https://api.goholiday.id
```

## 📈 Monitoring SSL

### Certificate Expiry Monitoring

Create monitoring script `/opt/monitor-ssl.sh`:
```bash
#!/bin/bash
DOMAIN="api.goholiday.id"
EXPIRY_DATE=$(echo | openssl s_client -connect $DOMAIN:443 -servername $DOMAIN 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt 30 ]; then
    echo "SSL certificate expires in $DAYS_LEFT days!" | mail -s "SSL Alert: $DOMAIN" admin@goholiday.id
fi
```

Add to cron:
```bash
# Check daily
0 9 * * * /opt/monitor-ssl.sh
```

### Nginx Performance Monitoring

```bash
# Check connection stats
docker exec dcnetwork-api-nginx nginx -s status 2>/dev/null || \
docker exec dcnetwork-api-nginx curl http://localhost:80/health/

# View access logs for traffic patterns
docker compose logs nginx | grep "GET /api/"
```

## ✅ Final SSL Checklist

After completing SSL setup:

- [ ] HTTPS loads successfully
- [ ] HTTP redirects to HTTPS
- [ ] Health check works: `curl https://api.goholiday.id/health/`
- [ ] Security headers present
- [ ] SSL Labs test shows A or A+
- [ ] Certificate auto-renewal configured (cron job active)
- [ ] Django `.env` has `SECURE_SSL_REDIRECT=true`
- [ ] Frontend uses HTTPS API URL
- [ ] Rate limiting working
- [ ] Media files accessible via HTTPS
- [ ] No mixed content warnings

## 📚 Additional Resources

- **SSL Labs Test**: https://www.ssllabs.com/ssltest/
- **Let's Encrypt Docs**: https://letsencrypt.org/docs/
- **Nginx SSL Guide**: https://nginx.org/en/docs/http/configuring_https_servers.html
- **Mozilla SSL Config**: https://ssl-config.mozilla.org/

---

**Quick Commands Reference:**

```bash
# Deploy without SSL
sudo ./deploy/deploy.sh

# Setup SSL
export SSL_EMAIL=your@email.com
sudo ./deploy/ssl-setup.sh

# Test SSL
curl https://api.goholiday.id/health/

# Check certificates
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Restart nginx
docker compose -f /opt/travel-marketplace-backend/docker-compose.prod.yml restart nginx

# View logs
docker compose logs -f nginx
```

---

**Your SSL configuration is production-ready and optimized for 2GB RAM!** 🎉

