#!/bin/bash
# Sync latest PostgreSQL backup to Google Drive
# Runs after backup_db.sh completes (scheduled via cron at 2:15 AM)
#
# Prerequisites:
#   - rclone installed and configured with a remote named "gdrive"
#   - rclone config at /root/.config/rclone/rclone.conf (or default location)
#
# Usage: ./sync_backup_gdrive.sh [--dry-run]

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/opt/ssmspl/backups}"
RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"
GDRIVE_FOLDER="${GDRIVE_FOLDER:-SSMSPL-Backups}"
GDRIVE_RETENTION_DAYS="${GDRIVE_RETENTION_DAYS:-30}"
LOG_FILE="${LOG_FILE:-/var/log/ssmspl-backup-sync.log}"
NOTIFY_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN="--dry-run"
    echo "[$(date)] DRY RUN MODE — no files will be uploaded or deleted"
fi

# ── Logging ─────────────────────────────────────────────────────────────────
exec > >(tee -a "${LOG_FILE}") 2>&1

echo ""
echo "================================================================"
echo "[$(date)] Starting Google Drive backup sync"
echo "================================================================"

# ── Find latest backup ──────────────────────────────────────────────────────
LATEST_BACKUP=$(find "${BACKUP_DIR}" -maxdepth 1 -name '*.sql.gz' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

if [[ -z "${LATEST_BACKUP}" ]]; then
    echo "[$(date)] ERROR: No backup files found in ${BACKUP_DIR}"
    if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
        "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "FAILED" "No backup files found in ${BACKUP_DIR}"
    fi
    exit 1
fi

# ── Guard against partially-written backups (backup_db.sh may still be running)
BACKUP_AGE_SECS=$(( $(date +%s) - $(stat -c%Y "${LATEST_BACKUP}") ))
if [[ ${BACKUP_AGE_SECS} -lt 300 ]]; then
    echo "[$(date)] WARNING: Latest backup is only ${BACKUP_AGE_SECS}s old — may still be in progress. Aborting."
    if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
        "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "WARNING" "Backup sync aborted — latest file is only ${BACKUP_AGE_SECS}s old, may still be writing"
    fi
    exit 1
fi

BACKUP_NAME=$(basename "${LATEST_BACKUP}")
BACKUP_SIZE=$(du -h "${LATEST_BACKUP}" | cut -f1)

echo "[$(date)] Latest backup: ${BACKUP_NAME} (${BACKUP_SIZE})"

# ── Check if already uploaded (skip duplicate uploads) ──────────────────────
if rclone ls "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/${BACKUP_NAME}" &>/dev/null; then
    echo "[$(date)] Backup ${BACKUP_NAME} already exists on Google Drive — skipping upload"
    echo "[$(date)] Sync complete (no new upload needed)"
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
                "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "WARNING" "Backup uploaded but size mismatch: local=${LOCAL_SIZE}, remote=${REMOTE_SIZE}"
            fi
            exit 1
        else
            echo "[$(date)] Verification: local=${LOCAL_SIZE} bytes, remote=${REMOTE_SIZE} bytes — OK"
        fi
    fi
else
    echo "[$(date)] ERROR: Upload failed!"
    if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
        "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "FAILED" "rclone upload failed for ${BACKUP_NAME}"
    fi
    exit 1
fi

# ── Success notification (sent before cleanup so a cleanup failure doesn't block it)
REMOTE_COUNT=$(rclone ls "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/" --include "*.sql.gz" 2>/dev/null | wc -l)

if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
    "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "SUCCESS" "Backup ${BACKUP_NAME} (${BACKUP_SIZE}) uploaded to Google Drive. ${REMOTE_COUNT} backups on GDrive."
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
