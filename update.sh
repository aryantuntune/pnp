#!/bin/bash
# ============================================================
# SSMSPL Graceful Update Script
# Deploys new code without showing 502 errors to users.
#
# What happens:
#   1. Enables "updates underway" mode (nginx serves maintenance pages)
#   2. Stops frontend & backend (nginx stays up, public site cached)
#   3. Rebuilds images with new code
#   4. Starts backend first, waits for health
#   5. Starts frontend, waits for health
#   6. Disables maintenance mode
#
# Usage:
#   git pull && ./update.sh
# ============================================================
set -e

COMPOSE_FILE="docker-compose.prod.yml"
MAINT_DIR="nginx/maintenance"
MAX_WAIT=90   # seconds to wait for a service to become healthy

# Color output helpers
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "\n${GREEN}[$1/6]${NC} $2"; }
warn() { echo -e "${YELLOW}WARNING:${NC} $1"; }
fail() { echo -e "${RED}FAILED:${NC} $1"; }

# Pre-flight check
if [ ! -f "$COMPOSE_FILE" ]; then
    fail "$COMPOSE_FILE not found. Run from project root."
    exit 1
fi

echo "============================================"
echo "  SSMSPL Graceful Update"
echo "============================================"

# Step 1: Enable update mode
step 1 "Enabling maintenance mode (updates underway)..."
touch "$MAINT_DIR/update.flag"
rm -f "$MAINT_DIR/maintenance.flag"
echo "  Admin portal  → Updates Underway"
echo "  Customer portal → Under Maintenance"
echo "  Public site   → Served from nginx cache"

# Step 2: Stop frontend and backend (nginx stays up)
step 2 "Stopping frontend and backend..."
docker compose -f $COMPOSE_FILE stop frontend backend
echo "  Frontend and backend stopped. Nginx still serving maintenance pages."

# Step 3: Rebuild images
step 3 "Rebuilding images..."
docker compose -f $COMPOSE_FILE build backend frontend
echo "  Images rebuilt successfully."

# Step 4: Start backend and wait for health
step 4 "Starting backend..."
docker compose -f $COMPOSE_FILE up -d backend
echo -n "  Waiting for backend health check"
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if docker compose -f $COMPOSE_FILE exec -T backend python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
        >/dev/null 2>&1; then
        echo -e " ${GREEN}healthy${NC}"
        break
    fi
    echo -n "."
    sleep 3
    elapsed=$((elapsed + 3))
done
if [ $elapsed -ge $MAX_WAIT ]; then
    warn "Backend didn't pass health check within ${MAX_WAIT}s. Continuing anyway..."
fi

# Step 5: Start frontend and wait for health
step 5 "Starting frontend..."
docker compose -f $COMPOSE_FILE up -d frontend
echo -n "  Waiting for frontend health check"
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if docker compose -f $COMPOSE_FILE exec -T frontend node -e \
        "const http = require('http'); http.get('http://localhost:3000', (r) => { process.exit(r.statusCode === 200 ? 0 : 1) }).on('error', () => process.exit(1))" \
        >/dev/null 2>&1; then
        echo -e " ${GREEN}healthy${NC}"
        break
    fi
    echo -n "."
    sleep 3
    elapsed=$((elapsed + 3))
done
if [ $elapsed -ge $MAX_WAIT ]; then
    warn "Frontend didn't pass health check within ${MAX_WAIT}s. Continuing anyway..."
fi

# Step 6: Disable maintenance mode
step 6 "Disabling maintenance mode..."
rm -f "$MAINT_DIR/update.flag" "$MAINT_DIR/maintenance.flag"
echo "  All portals back to normal operation."

echo ""
echo "============================================"
echo -e "  ${GREEN}Update complete!${NC}"
echo "============================================"
echo ""
echo "  Site:  https://carferry.online"
echo "  API:   https://api.carferry.online"
echo "  Admin: https://carferry.online/login"
echo ""

# Quick container status
docker compose -f $COMPOSE_FILE ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || \
    docker compose -f $COMPOSE_FILE ps
