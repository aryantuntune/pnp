#!/bin/bash
# refresh_admin_db.sh — Copy ssmspl_sync (read-only replica) → ssmspl_admin (editable)
# Run on Server 2 as root or postgres user
#
# Usage:
#   sudo ./refresh_admin_db.sh
#   # Or via cron: 0 3 * * * /var/www/ssmspl-admin/scripts/refresh_admin_db.sh >> /var/log/ssmspl_admin_refresh.log 2>&1

set -euo pipefail

SYNC_DB="ssmspl_sync"
ADMIN_DB="ssmspl_admin"
ADMIN_USER="ssmspl_admin_user"
DUMP_FILE="/tmp/ssmspl_sync_dump_$(date +%Y%m%d_%H%M%S).sql"

echo "[$(date)] === Starting refresh: $SYNC_DB → $ADMIN_DB ==="

# Step 1: Dump ssmspl_sync (excluding replication objects)
echo "[$(date)] Dumping $SYNC_DB..."
sudo -u postgres pg_dump -d "$SYNC_DB" \
    --no-owner --no-privileges \
    --clean --if-exists \
    --no-publications --no-subscriptions \
    > "$DUMP_FILE"

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "[$(date)] Dump complete: $DUMP_FILE ($DUMP_SIZE)"

# Step 2: Restore into ssmspl_admin
echo "[$(date)] Restoring into $ADMIN_DB..."
ERRORS=$(sudo -u postgres psql -d "$ADMIN_DB" -f "$DUMP_FILE" 2>&1 | grep -cE "^(ERROR|FATAL)" || true)
if [ "$ERRORS" -gt 0 ]; then
    echo "[$(date)] WARNING: $ERRORS error(s) during restore — check logs"
fi

# Step 3: Re-grant permissions to admin user
echo "[$(date)] Re-granting permissions to $ADMIN_USER..."
sudo -u postgres psql -d "$ADMIN_DB" -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO $ADMIN_USER;"
sudo -u postgres psql -d "$ADMIN_DB" -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO $ADMIN_USER;"

# Step 4: Reset all sequences to match restored data
echo "[$(date)] Resetting sequences..."
sudo -u postgres psql -d "$ADMIN_DB" -c "
DO \$\$
DECLARE r RECORD;
BEGIN
    FOR r IN
        SELECT sequencename, split_part(sequencename, '_id_seq', 1) AS tbl
        FROM pg_sequences WHERE schemaname = 'public'
    LOOP
        EXECUTE format(
            'SELECT setval(''public.%I'', COALESCE((SELECT MAX(id) FROM public.%I), 1))',
            r.sequencename, r.tbl
        );
    END LOOP;
END \$\$;
"

# Step 5: Post-restore health check
echo "[$(date)] Verifying critical tables..."
TABLE_COUNT=$(sudo -u postgres psql -d "$ADMIN_DB" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
echo "[$(date)] Tables in $ADMIN_DB: $TABLE_COUNT"

# Step 6: Cleanup
rm -f "$DUMP_FILE"

echo "[$(date)] === Refresh complete ==="
