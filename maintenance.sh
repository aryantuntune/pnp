#!/bin/bash
# ============================================================
# SSMSPL Maintenance Mode Toggle
# Controls what users see when the site is down.
#
# Usage:
#   ./maintenance.sh on        General maintenance (both portals: "under maintenance")
#   ./maintenance.sh update    Update mode (admin: "updates underway", customer: "under maintenance")
#   ./maintenance.sh off       Disable maintenance mode
#   ./maintenance.sh status    Show current mode
# ============================================================
set -e

MAINT_DIR="nginx/maintenance"

if [ ! -d "$MAINT_DIR" ]; then
    echo "ERROR: $MAINT_DIR directory not found. Are you in the project root?"
    exit 1
fi

case "${1:-}" in
    on)
        touch "$MAINT_DIR/maintenance.flag"
        rm -f "$MAINT_DIR/update.flag"
        echo "Maintenance mode: ON"
        echo "  Admin portal  → Under Maintenance"
        echo "  Customer portal → Under Maintenance"
        echo "  Public site   → Served from cache (or fallback page)"
        ;;
    update)
        touch "$MAINT_DIR/update.flag"
        rm -f "$MAINT_DIR/maintenance.flag"
        echo "Maintenance mode: UPDATE"
        echo "  Admin portal  → Updates Underway"
        echo "  Customer portal → Under Maintenance"
        echo "  Public site   → Served from cache (or fallback page)"
        ;;
    off)
        rm -f "$MAINT_DIR/maintenance.flag" "$MAINT_DIR/update.flag"
        echo "Maintenance mode: OFF"
        echo "  All portals → Normal operation"
        ;;
    status)
        if [ -f "$MAINT_DIR/update.flag" ]; then
            echo "Mode: UPDATE (updates underway)"
        elif [ -f "$MAINT_DIR/maintenance.flag" ]; then
            echo "Mode: MAINTENANCE (under maintenance)"
        else
            echo "Mode: NORMAL (no maintenance flags set)"
        fi
        ;;
    *)
        echo "SSMSPL Maintenance Mode Toggle"
        echo ""
        echo "Usage: $0 {on|update|off|status}"
        echo ""
        echo "  on      — General maintenance mode"
        echo "  update  — Update/deployment mode (admin sees 'updates underway')"
        echo "  off     — Disable maintenance mode"
        echo "  status  — Show current mode"
        exit 1
        ;;
esac
