#!/bin/bash
# Sync latest PostgreSQL backup to Google Drive
# Runs on the HOST via cron (every 5 minutes checking for .sync_needed,
# or daily at 2:15 AM as a safety net).
#
# Prerequisites:
#   - rclone installed and configured with a remote named "gdrive"
#   - rclone config at /root/.config/rclone/rclone.conf (or default location)
#   - jq installed (recommended) OR python3 (fallback for JSON log)
#
# Usage:
#   ./sync_backup_gdrive.sh              # Only syncs if .sync_needed exists
#   ./sync_backup_gdrive.sh --force      # Sync regardless of trigger file
#   ./sync_backup_gdrive.sh --dry-run    # Simulate upload (no changes)

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/var/www/ssmspl/backups}"
RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"
GDRIVE_FOLDER="${GDRIVE_FOLDER:-SSMSPL-Backups}"
GDRIVE_RETENTION_DAYS="${GDRIVE_RETENTION_DAYS:-30}"
LOG_FILE="${LOG_FILE:-/var/log/ssmspl-backup-sync.log}"
NOTIFY_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_NEEDED_FILE="${BACKUP_DIR}/.sync_needed"

DRY_RUN=""
FORCE=""
for arg in "$@"; do
    case "${arg}" in
        --dry-run) DRY_RUN="--dry-run"; echo "[$(date)] DRY RUN MODE — no files will be uploaded or deleted" ;;
        --force)   FORCE="1" ;;
    esac
done

# ── Check if sync is needed ────────────────────────────────────────────────
if [[ -z "${FORCE}" && ! -f "${SYNC_NEEDED_FILE}" ]]; then
    # Nothing to sync — exit silently (cron runs this every 5 min)
    exit 0
fi

# ── Lock file — prevent concurrent sync runs ───────────────────────────────
LOCK_FILE="/tmp/ssmspl-backup-sync.lock"
exec 200>"${LOCK_FILE}"
if ! flock -n 200; then
    echo "[$(date)] Another sync is already running — exiting"
    exit 0
fi

# ── Logging ─────────────────────────────────────────────────────────────────
exec > >(tee -a "${LOG_FILE}") 2>&1

echo ""
echo "================================================================"
echo "[$(date)] Starting Google Drive backup sync"
echo "================================================================"

# ── Find latest backup ──────────────────────────────────────────────────────
LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | head -1)

if [[ -z "${LATEST_BACKUP}" ]]; then
    echo "[$(date)] ERROR: No backup files found in ${BACKUP_DIR}"
    if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
        "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "FAILED" "No backup files found in ${BACKUP_DIR}" || true
    fi
    exit 1
fi

BACKUP_NAME=$(basename "${LATEST_BACKUP}")
BACKUP_SIZE=$(du -h "${LATEST_BACKUP}" | cut -f1)

echo "[$(date)] Latest backup: ${BACKUP_NAME} (${BACKUP_SIZE})"

# ── Verify backup is confirmed complete by backup_db.sh ─────────────────────
BACKUP_STATUS_FILE="${BACKUP_DIR}/.last_backup.json"
if [[ -f "${BACKUP_STATUS_FILE}" ]]; then
    # Parse status file to check the latest confirmed backup
    CONFIRMED_FILE=$(grep -o '"file":"[^"]*"' "${BACKUP_STATUS_FILE}" | head -1 | cut -d'"' -f4)
    CONFIRMED_STATUS=$(grep -o '"status":"[^"]*"' "${BACKUP_STATUS_FILE}" | head -1 | cut -d'"' -f4)

    if [[ "${CONFIRMED_FILE}" != "${BACKUP_NAME}" ]]; then
        echo "[$(date)] WARNING: Latest file ${BACKUP_NAME} not confirmed by status file (confirmed: ${CONFIRMED_FILE:-none}). Backup may still be running. Skipping."
        # Don't remove .sync_needed — retry on next cron run
        exit 0
    fi
    if [[ "${CONFIRMED_STATUS}" != "success" ]]; then
        echo "[$(date)] WARNING: Latest backup ${BACKUP_NAME} has status '${CONFIRMED_STATUS}'. Skipping sync."
        rm -f "${SYNC_NEEDED_FILE}"
        exit 0
    fi
    echo "[$(date)] Status file confirms ${BACKUP_NAME} completed successfully"
else
    # No status file — fall back to age-based guard
    BACKUP_MTIME=$(stat -c%Y "${LATEST_BACKUP}" 2>/dev/null || date -r "${LATEST_BACKUP}" +%s)
    BACKUP_AGE_SECS=$(( $(date +%s) - BACKUP_MTIME ))
    if [[ ${BACKUP_AGE_SECS} -lt 120 ]]; then
        echo "[$(date)] WARNING: No status file and backup is only ${BACKUP_AGE_SECS}s old — may still be in progress. Skipping."
        exit 0
    fi
    echo "[$(date)] WARNING: No status file found — proceeding based on file age (${BACKUP_AGE_SECS}s)"
fi

# ── Check if already uploaded (skip duplicate uploads) ──────────────────────
if rclone ls "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/${BACKUP_NAME}" &>/dev/null; then
    echo "[$(date)] Backup ${BACKUP_NAME} already exists on Google Drive — skipping upload"
    echo "[$(date)] Sync complete (no new upload needed)"
    rm -f "${SYNC_NEEDED_FILE}"
    exit 0
fi

# ── Upload to Google Drive ──────────────────────────────────────────────────
echo "[$(date)] Uploading ${BACKUP_NAME} to ${RCLONE_REMOTE}:${GDRIVE_FOLDER}/ ..."

if rclone copy ${DRY_RUN} \
    "${LATEST_BACKUP}" \
    "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/" \
    --progress \
    --stats-one-line \
    --retries 3 \
    --retries-sleep 10s; then

    echo "[$(date)] Upload successful"

    # ── Verify upload ───────────────────────────────────────────────────
    if [[ -z "${DRY_RUN}" ]]; then
        REMOTE_SIZE=$(rclone size "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/${BACKUP_NAME}" --json 2>/dev/null | grep -o '"bytes":[0-9]*' | cut -d: -f2)
        LOCAL_SIZE=$(stat -c%s "${LATEST_BACKUP}" 2>/dev/null || stat -f%z "${LATEST_BACKUP}")

        if [[ -z "${REMOTE_SIZE}" ]]; then
            echo "[$(date)] WARNING: Could not retrieve remote file size (rclone size failed). Skipping verification."
        elif [[ "${REMOTE_SIZE}" != "${LOCAL_SIZE}" ]]; then
            echo "[$(date)] WARNING: Size mismatch! local=${LOCAL_SIZE} bytes, remote=${REMOTE_SIZE} bytes"
            if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
                "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "WARNING" "Backup uploaded but size mismatch: local=${LOCAL_SIZE}, remote=${REMOTE_SIZE}" || true
            fi
            exit 1
        else
            echo "[$(date)] Verification: local=${LOCAL_SIZE} bytes, remote=${REMOTE_SIZE} bytes — OK"
        fi
    fi
else
    echo "[$(date)] ERROR: Upload failed!"
    cat > "${BACKUP_DIR}/.sync_status.json.tmp" <<STATUSEOF
{"time":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","file":"${BACKUP_NAME:-unknown}","status":"failed","gdrive_count":0}
STATUSEOF
    mv "${BACKUP_DIR}/.sync_status.json.tmp" "${BACKUP_DIR}/.sync_status.json"
    if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
        "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "FAILED" "rclone upload failed for ${BACKUP_NAME}" || true
    fi
    exit 1
fi

# ── Write sync status for backend API ───────────────────────────────────
REMOTE_COUNT=$(rclone ls "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/" --include "*.sql.gz" 2>/dev/null | wc -l)

cat > "${BACKUP_DIR}/.sync_status.json.tmp" <<STATUSEOF
{"time":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","file":"${BACKUP_NAME}","status":"success","gdrive_count":${REMOTE_COUNT}}
STATUSEOF
mv "${BACKUP_DIR}/.sync_status.json.tmp" "${BACKUP_DIR}/.sync_status.json"

# ── Update sync log (keeps last 60 entries for history API) ─────────────
SYNC_LOG="${BACKUP_DIR}/.sync_log.json"
SYNC_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if command -v jq &>/dev/null; then
    # Preferred: use jq (safe, no injection risk)
    if [ -f "${SYNC_LOG}" ] && [ -s "${SYNC_LOG}" ]; then
        jq --arg file "${BACKUP_NAME}" --arg time "${SYNC_TIME}" \
            '[{"file": $file, "time": $time, "status": "success"}] + . | .[0:60]' \
            "${SYNC_LOG}" > "${SYNC_LOG}.tmp" 2>/dev/null \
            && mv "${SYNC_LOG}.tmp" "${SYNC_LOG}" \
            || echo "[$(date)] WARNING: jq failed to update sync log"
    else
        jq -n --arg file "${BACKUP_NAME}" --arg time "${SYNC_TIME}" \
            '[{"file": $file, "time": $time, "status": "success"}]' > "${SYNC_LOG}"
    fi
elif command -v python3 &>/dev/null; then
    # Fallback: python3 with env vars (no shell injection)
    SYNC_LOG_PATH="${SYNC_LOG}" SYNC_BACKUP_NAME="${BACKUP_NAME}" SYNC_TIME="${SYNC_TIME}" \
    python3 << 'PYEOF'
import json, os
log_file = os.environ['SYNC_LOG_PATH']
try:
    with open(log_file) as f:
        log = json.load(f)
except (FileNotFoundError, json.JSONDecodeError, ValueError):
    log = []
log.insert(0, {
    'file': os.environ['SYNC_BACKUP_NAME'],
    'time': os.environ['SYNC_TIME'],
    'status': 'success'
})
log = log[:60]
with open(log_file, 'w') as f:
    json.dump(log, f)
PYEOF
else
    # Last resort: overwrite with single entry (better than nothing)
    echo "[{\"file\":\"${BACKUP_NAME}\",\"time\":\"${SYNC_TIME}\",\"status\":\"success\"}]" > "${SYNC_LOG}"
    echo "[$(date)] WARNING: Neither jq nor python3 found — sync log has only latest entry"
fi

# ── Remove sync trigger (we're done) ──────────────────────────────────────
rm -f "${SYNC_NEEDED_FILE}"

# ── Success notification (sent before cleanup so a cleanup failure doesn't block it)
if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
    "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "SUCCESS" "Backup ${BACKUP_NAME} (${BACKUP_SIZE}) uploaded to Google Drive. ${REMOTE_COUNT} backups on GDrive." || true
fi

# ── Rotate old backups on Google Drive (non-fatal) ──────────────────────────
echo "[$(date)] Cleaning up backups older than ${GDRIVE_RETENTION_DAYS} days on Google Drive..."

if ! rclone delete ${DRY_RUN} \
    "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/" \
    --min-age "${GDRIVE_RETENTION_DAYS}d" \
    --include "*.sql.gz"; then
    echo "[$(date)] WARNING: Google Drive cleanup failed (non-fatal, upload was successful)"
fi

REMOTE_COUNT=$(rclone ls "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/" --include "*.sql.gz" 2>/dev/null | wc -l)
echo "[$(date)] Google Drive retention: ${REMOTE_COUNT} backups remaining"

echo "[$(date)] Sync complete"
