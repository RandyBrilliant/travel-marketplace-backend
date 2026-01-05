# Mailgun Email Fix - Port 587 Blocked

## Problem
Your server's firewall is blocking outbound SMTP port 587, preventing email delivery via SMTP.

**Test result:**
```
✗ Port 587 is not reachable (error code: 11)
This might be a firewall or network issue
```

## Solution
Use Mailgun's **HTTP API** instead of SMTP to bypass the port block.

---

## Setup Instructions

### 1. Get Your Mailgun API Key

1. Log in to [Mailgun Dashboard](https://app.mailgun.com/)
2. Go to **Settings** → **API Keys**
3. Copy your **Private API Key** (starts with `key-...`)
4. Note your **Domain** (e.g., `goholiday.id` or `mg.goholiday.id`)

### 2. Update Your Production `.env` File

SSH into your server and edit the `.env` file:

```bash
cd ~/travel-marketplace-backend
nano .env
```

**Replace the SMTP email configuration with:**

```bash
# Email Configuration (Mailgun HTTP API)
MAILGUN_API_KEY=key-your-actual-private-api-key-here
MAILGUN_DOMAIN=goholiday.id
DEFAULT_FROM_EMAIL=noreply@goholiday.id
FRONTEND_URL=https://www.goholiday.id
```

**Remove or comment out these SMTP lines:**
```bash
# MAILGUN_SMTP_SERVER=smtp.mailgun.org
# MAILGUN_SMTP_PORT=587
# MAILGUN_SMTP_LOGIN=...
# MAILGUN_SMTP_PASSWORD=...
```

If you're using Mailgun EU region, also add:
```bash
MAILGUN_API_URL=https://api.eu.mailgun.net/v3
```

Save and exit (Ctrl+X, Y, Enter in nano).

### 3. Rebuild and Restart Services

```bash
# Rebuild containers with new dependencies
docker compose -f docker-compose.prod.yml build api celery

# Restart all services
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# Check services are running
docker compose -f docker-compose.prod.yml ps
```

### 4. Verify Email Works

Watch the Celery logs:
```bash
docker compose -f docker-compose.prod.yml logs -f celery
```

Then try sending a verification email from your app. You should see:
```
✓ Verification email sent successfully to user@example.com
```

---

## Why This Works

- **SMTP (Port 587)**: Requires opening a network port that many VPS providers block
- **HTTP API (Port 443)**: Uses HTTPS like any web request - never blocked
- **Same functionality**: Both methods send emails through Mailgun

---

## Troubleshooting

### If you see "Invalid API key"
- Double-check you copied the **Private API Key** (not the public one)
- Ensure no extra spaces in the `.env` file

### If you see "Domain not found"
- Verify the domain matches your Mailgun dashboard exactly
- Use the sending domain, not a subdomain (unless you set up a subdomain)

### If emails still don't send
Check the logs for specific errors:
```bash
docker compose -f docker-compose.prod.yml logs celery | grep -i error
```

### To test the configuration
```bash
docker compose -f docker-compose.prod.yml exec celery python manage.py test_email
```

---

## Alternative: Open Port 587 (Not Recommended)

If you prefer SMTP, contact your VPS provider to:
1. Open outbound port 587
2. Remove from spam prevention blocks

However, the HTTP API is simpler and more reliable.

