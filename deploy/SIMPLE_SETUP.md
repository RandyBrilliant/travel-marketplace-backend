# Simple Setup - No More /opt/ Hardcoding!

All scripts now automatically detect their location. No need to set `APP_DIR` manually!

## ✅ How It Works Now

Scripts automatically use their current directory:

```bash
# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="${APP_DIR:-$(dirname "$SCRIPT_DIR")}"
```

This means:
- If you're in `/home/regretzz/travel-marketplace-backend` → uses that
- If you're in `/opt/travel-marketplace-backend` → uses that  
- If you're anywhere else → uses that location

## 🚀 Quick Start

### 1. Just Run Scripts Directly

```bash
cd /home/regretzz/travel-marketplace-backend

# No APP_DIR needed!
sudo ./deploy/optimize-2gb.sh
sudo ./deploy/deploy.sh
```

### 2. Or Use Aliases (Optional)

```bash
# Add to ~/.bashrc (optional, for convenience)
alias tm-deploy='cd ~/travel-marketplace-backend && sudo ./deploy/deploy.sh'
alias tm-update='cd ~/travel-marketplace-backend && sudo ./deploy/rolling-update.sh'
alias tm-logs='docker compose -f ~/travel-marketplace-backend/docker-compose.prod.yml logs -f'
```

## 📋 All Scripts Work From Any Location

```bash
# From project root
cd /home/regretzz/travel-marketplace-backend
sudo ./deploy/deploy.sh

# From deploy directory
cd /home/regretzz/travel-marketplace-backend/deploy
sudo ./deploy.sh

# From anywhere with full path
sudo /home/regretzz/travel-marketplace-backend/deploy/deploy.sh
```

## 🔧 Scripts Updated

All these scripts now auto-detect location:

- ✅ `deploy.sh` - Main deployment
- ✅ `update.sh` - Quick update
- ✅ `rolling-update.sh` - Minimal downtime update
- ✅ `optimize-2gb.sh` - System optimization
- ✅ `ssl-setup.sh` - SSL setup
- ✅ `backup.sh` - Database backup
- ✅ `fresh-start.sh` - Fresh deployment
- ✅ `complete-reset.sh` - Complete reset
- ✅ `ubuntu-setup.sh` - Initial server setup

## 🎯 Your Current Setup

```bash
# Your directory
/home/regretzz/travel-marketplace-backend

# Just run scripts
sudo ./deploy/deploy.sh           # ✅ Works!
sudo ./deploy/optimize-2gb.sh     # ✅ Works!
sudo ./deploy/rolling-update.sh   # ✅ Works!
```

## 🛠️ Override If Needed

If you ever need to override (rare):

```bash
APP_DIR=/custom/path sudo -E ./deploy/deploy.sh
```

But you shouldn't need to - scripts auto-detect!

---

**That's it! No more path configuration needed.** 🎉

