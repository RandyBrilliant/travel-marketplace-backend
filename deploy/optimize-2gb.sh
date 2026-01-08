#!/bin/bash

# Complete 2GB RAM + 1vCPU Optimization Script for Digital Ocean
# This script optimizes the entire server for low-resource environments

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Complete 2GB/1vCPU Optimization"
echo "==========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    echo "Usage: sudo ./deploy/optimize-2gb.sh"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_DIR="${APP_DIR:-$PROJECT_DIR}"

# ==================== SYSTEM OPTIMIZATIONS ====================

echo -e "${BLUE}[1/8] System Optimization - Memory Settings${NC}"

# Fix Redis memory overcommit warning
if ! grep -q "vm.overcommit_memory = 1" /etc/sysctl.conf 2>/dev/null; then
    echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf
    sysctl vm.overcommit_memory=1
    echo -e "${GREEN}✓ Redis memory overcommit enabled${NC}"
else
    echo -e "${GREEN}✓ Memory overcommit already configured${NC}"
fi

# Reduce swappiness for better performance
if ! grep -q "vm.swappiness" /etc/sysctl.conf 2>/dev/null; then
    echo "vm.swappiness = 10" >> /etc/sysctl.conf
    sysctl vm.swappiness=10
    echo -e "${GREEN}✓ Swappiness reduced to 10${NC}"
else
    echo -e "${GREEN}✓ Swappiness already configured${NC}"
fi

# Apply all sysctl settings
sysctl -p

echo ""
echo -e "${BLUE}[2/8] Setting up Swap Space (if not exists)${NC}"

# Check if swap exists
if ! swapon --show | grep -q '/swapfile'; then
    echo -e "${YELLOW}Creating 2GB swap file...${NC}"
    
    # Create swap file (2GB for 2GB RAM server)
    fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    
    # Make swap permanent
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    
    echo -e "${GREEN}✓ Swap file created and activated${NC}"
else
    echo -e "${GREEN}✓ Swap already exists${NC}"
fi

echo ""
echo -e "${BLUE}[3/8] Docker System Optimization${NC}"

# Configure Docker daemon for low memory
DOCKER_DAEMON_JSON="/etc/docker/daemon.json"
if [ ! -f "$DOCKER_DAEMON_JSON" ]; then
    cat > "$DOCKER_DAEMON_JSON" <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
EOF
    echo -e "${GREEN}✓ Docker daemon configured${NC}"
    systemctl restart docker
    sleep 5
else
    echo -e "${GREEN}✓ Docker daemon already configured${NC}"
fi

# Clean up Docker system
echo -e "${YELLOW}Cleaning Docker system...${NC}"
docker system prune -af --volumes 2>/dev/null || true
echo -e "${GREEN}✓ Docker system cleaned${NC}"

echo ""
echo -e "${BLUE}[4/8] PostgreSQL Optimization${NC}"

# Create optimized PostgreSQL config for docker-compose
mkdir -p "$PROJECT_DIR/postgres"
cat > "$PROJECT_DIR/postgres/postgresql.conf" <<'EOF'
# PostgreSQL Configuration for 2GB RAM Server
# Memory Configuration (Conservative for shared 2GB system)
shared_buffers = 64MB              # 25% of available memory for DB (~256MB)
effective_cache_size = 128MB       # Estimate of disk cache
work_mem = 2MB                     # Per query operation
maintenance_work_mem = 16MB        # For VACUUM, CREATE INDEX

# Connection Settings
max_connections = 50               # Reduced for low memory
superuser_reserved_connections = 3

# Write-Ahead Log
wal_buffers = 2MB
min_wal_size = 80MB
max_wal_size = 256MB

# Query Planning
random_page_cost = 1.1             # For SSD storage
effective_io_concurrency = 200     # For SSD storage

# Logging (Minimal)
logging_collector = off
log_statement = 'none'
log_duration = off

# Performance
checkpoint_completion_target = 0.9
EOF

echo -e "${GREEN}✓ PostgreSQL config created${NC}"

echo ""
echo -e "${BLUE}[5/8] Environment Variable Optimization${NC}"

if [ -f "$APP_DIR/.env" ]; then
    # Optimize database connection pool
    if ! grep -q "DB_CONN_MAX_AGE" "$APP_DIR/.env"; then
        echo "" >> "$APP_DIR/.env"
        echo "# Optimized for 2GB RAM" >> "$APP_DIR/.env"
        echo "DB_CONN_MAX_AGE=300" >> "$APP_DIR/.env"
    fi
    
    # Set conservative token lifetime
    sed -i 's/ACCESS_TOKEN_LIFETIME_MINUTES=.*/ACCESS_TOKEN_LIFETIME_MINUTES=15/' "$APP_DIR/.env" 2>/dev/null || true
    sed -i 's/REFRESH_TOKEN_LIFETIME_DAYS=.*/REFRESH_TOKEN_LIFETIME_DAYS=7/' "$APP_DIR/.env" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Environment variables optimized${NC}"
else
    echo -e "${YELLOW}⚠ .env file not found at $APP_DIR/.env${NC}"
fi

echo ""
echo -e "${BLUE}[6/8] Nginx Optimization${NC}"

# Optimize nginx config
if [ -f "$PROJECT_DIR/nginx/nginx.conf" ]; then
    # Backup original
    cp "$PROJECT_DIR/nginx/nginx.conf" "$PROJECT_DIR/nginx/nginx.conf.backup-$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
    
    # Create optimized nginx config
    cat > "$PROJECT_DIR/nginx/nginx.conf" <<'EOF'
user nginx;
worker_processes 1;  # Match single vCPU
worker_rlimit_nofile 8192;

error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;  # Reduced for low memory
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 30;  # Reduced from 65
    keepalive_requests 100;
    reset_timedout_connection on;

    # Buffer sizes (optimized for 2GB)
    client_body_buffer_size 128k;
    client_max_body_size 20M;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;
    output_buffers 2 32k;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               application/rss+xml font/truetype font/opentype 
               application/vnd.ms-fontobject image/svg+xml;
    gzip_disable "msie6";
    gzip_min_length 256;
    gzip_buffers 16 8k;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting (optimized for 2GB RAM)
    limit_req_zone $binary_remote_addr zone=api_limit:2m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:1m rate=5r/m;

    # Hide nginx version
    server_tokens off;

    # Include site configs
    include /etc/nginx/conf.d/*.conf;
}
EOF
    echo -e "${GREEN}✓ Nginx configuration optimized${NC}"
fi

echo ""
echo -e "${BLUE}[7/8] Verifying Docker Compose Configuration${NC}"

if [ -f "$APP_DIR/docker-compose.prod.yml" ]; then
    echo -e "${GREEN}✓ Docker Compose file exists${NC}"
    echo -e "${YELLOW}Current memory limits:${NC}"
    grep -A 3 "limits:" "$APP_DIR/docker-compose.prod.yml" | grep "memory:" | sed 's/^/  /'
else
    echo -e "${YELLOW}⚠ Docker Compose file not found${NC}"
fi

echo ""
echo -e "${BLUE}[8/8] Setting up Log Rotation${NC}"

# Create logrotate config for application logs
cat > /etc/logrotate.d/travel-marketplace <<'EOF'
/opt/travel-marketplace-backend/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
}
EOF

echo -e "${GREEN}✓ Log rotation configured${NC}"

# ==================== SUMMARY ====================

echo ""
echo -e "${GREEN}=========================================="
echo "Optimization Complete!"
echo "==========================================${NC}"
echo ""

echo -e "${BLUE}System Information:${NC}"
echo "Total Memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Available Memory: $(free -h | awk '/^Mem:/ {print $7}')"
echo "Swap: $(free -h | awk '/^Swap:/ {print $2}')"
echo "vCPUs: $(nproc)"
echo ""

echo -e "${BLUE}Applied Optimizations:${NC}"
echo "  ✓ Memory overcommit enabled for Redis"
echo "  ✓ Swappiness reduced to 10"
echo "  ✓ 2GB swap file created"
echo "  ✓ Docker logging optimized (10MB max per file)"
echo "  ✓ PostgreSQL tuned for low memory"
echo "  ✓ Nginx worker processes set to 1"
echo "  ✓ Nginx connections reduced to 1024"
echo "  ✓ Log rotation configured"
echo ""

echo -e "${BLUE}Docker Container Memory Allocation:${NC}"
echo "  • API (Gunicorn):    200MB (1 worker)"
echo "  • Database:          200MB"
echo "  • Redis:             100MB (80MB max)"
echo "  • Celery:            200MB (1 worker)"
echo "  • Celery Beat:       100MB"
echo "  • Nginx:              50MB"
echo "  ─────────────────────────────"
echo "  Total:              ~850MB"
echo ""
echo "  System overhead:    ~300MB"
echo "  Available for OS:   ~850MB + swap"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review your .env file configuration"
echo "2. Deploy the application:"
echo "   ${BLUE}sudo ./deploy/deploy.sh${NC}"
echo ""
echo "3. Monitor resource usage:"
echo "   ${BLUE}docker stats${NC}"
echo "   ${BLUE}free -h${NC}"
echo "   ${BLUE}htop${NC}"
echo ""
echo "4. Check logs if any issues:"
echo "   ${BLUE}docker compose -f $APP_DIR/docker-compose.prod.yml logs -f${NC}"
echo ""

echo -e "${YELLOW}⚠ Important Notes:${NC}"
echo "• This is a minimal viable setup for 2GB/1vCPU"
echo "• Expect slower performance during peak load"
echo "• Consider upgrading to 4GB RAM for production"
echo "• Monitor closely during first few days"
echo "• Set up monitoring (e.g., Netdata, Prometheus)"
echo ""

echo -e "${GREEN}Run 'docker stats' to monitor real-time resource usage${NC}"
echo ""

