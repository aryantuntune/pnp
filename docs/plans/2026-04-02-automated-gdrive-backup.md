# Automated Google Drive Backup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically upload daily PostgreSQL backups to Google Drive with email notifications, so the business has off-server disaster recovery.

**Architecture:** The existing `db-backup` Docker service already creates compressed `pg_dump` files daily at 2:00 AM into a Docker volume. This plan adds a host-level cron job that runs 15 minutes after the backup, uses `rclone` to sync the latest backup to Google Drive, manages retention (30 days on GDrive), and sends an email notification on success or failure.

**Tech Stack:** rclone (Google Drive sync), msmtp (lightweight SMTP for email), bash, cron

---

## Current State

- `backend/scripts/backup_db.sh` runs daily at 2:00 AM via the `db-backup` Docker service
- Backups are gzip-compressed `pg_dump` files (~small, ticketing system DB)
- Stored in Docker named volume `db-backups` mounted at `/backups` inside the container
- 7-day retention on-server
- **Problem:** Backups never leave the server. If the VPS dies, everything is lost.

## What Changes

| Component | Change |
|---|---|
| `docker-compose.prod.yml` | Change `db-backups` from named volume to bind mount (`./backups`) |
| `backend/scripts/sync_backup_gdrive.sh` | **New** — uploads latest backup to Google Drive, manages GDrive retention |
| `backend/scripts/notify_backup.sh` | **New** — sends email notification (success/failure) |
| Host cron | **New** — runs sync script daily at 2:15 AM |

## Credentials Required (to be added by user)

1. **Google Drive:** rclone OAuth token (interactive setup via `rclone config`)
2. **Email (Gmail SMTP):** Gmail address + App Password (16-char code from Google Account > Security > App Passwords)

---

### Task 1: Change Docker Backup Volume to Bind Mount

**Why:** Named volumes are buried in `/var/lib/docker/volumes/`. A bind mount at `./backups` makes the backup files directly accessible to host-level scripts without needing `docker cp`.

**Files:**
- Modify: `docker-compose.prod.yml`

- [ ] **Step 1: Update docker-compose.prod.yml — change volume to bind mount**

In `docker-compose.prod.yml`, make two changes:

**Change 1 — `db-backup` service volumes section:**
```yaml
# BEFORE
    volumes:
      - ./backend/scripts/backup_db.sh:/scripts/backup_db.sh:ro
      - db-backups:/backups

# AFTER
    volumes:
      - ./backend/scripts/backup_db.sh:/scripts/backup_db.sh:ro
      - ./backups:/backups
```

**Change 2 — Remove `db-backups` from the named volumes block at the bottom:**
```yaml
# BEFORE
volumes:
  pg_data:
  db-backups:

# AFTER
volumes:
  pg_data:
```

- [ ] **Step 2: Create the backups directory and add .gitignore**

```bash
mkdir -p /path/to/ssmspl/backups
echo "*.sql.gz" > /path/to/ssmspl/backups/.gitignore
```

This keeps backup files out of git while preserving the directory.

- [ ] **Step 3: Verify existing backups are preserved**

Before restarting Docker, copy any existing backups from the named volume:

```bash
# On the VPS:
docker cp ssmspl-db-backup-1:/backups/. ./backups/
```

Then restart the db-backup service:

```bash
docker compose -f docker-compose.prod.yml up -d db-backup
```

Verify backups appear in `./backups/`:

```bash
ls -lh ./backups/
```

Expected: existing `.sql.gz` files listed with dates and sizes.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.prod.yml backups/.gitignore
git commit -m "chore: change db-backup volume to bind mount for host-level access"
```

---

### Task 2: Create the Google Drive Sync Script

**Files:**
- Create: `backend/scripts/sync_backup_gdrive.sh`

- [ ] **Step 1: Create the sync script**

Create `backend/scripts/sync_backup_gdrive.sh`:

```bash
#!/bin/bash
# Sync latest PostgreSQL backup to Google Drive
# Runs after backup_db.sh completes (scheduled via cron)
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
NOTIFY_SCRIPT_DIR="$(dirname "$0")"

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
LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | head -1)

if [[ -z "${LATEST_BACKUP}" ]]; then
    echo "[$(date)] ERROR: No backup files found in ${BACKUP_DIR}"
    # Send failure notification
    if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
        "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "FAILED" "No backup files found in ${BACKUP_DIR}"
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
        echo "[$(date)] Verification: local=${LOCAL_SIZE} bytes, remote=${REMOTE_SIZE} bytes"

        if [[ "${REMOTE_SIZE}" != "${LOCAL_SIZE}" ]]; then
            echo "[$(date)] WARNING: Size mismatch! Upload may be corrupted."
            if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
                "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "WARNING" "Backup uploaded but size mismatch detected: local=${LOCAL_SIZE}, remote=${REMOTE_SIZE}"
            fi
            exit 1
        fi
    fi
else
    echo "[$(date)] ERROR: Upload failed!"
    if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
        "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "FAILED" "rclone upload failed for ${BACKUP_NAME}"
    fi
    exit 1
fi

# ── Rotate old backups on Google Drive ──────────────────────────────────────
echo "[$(date)] Cleaning up backups older than ${GDRIVE_RETENTION_DAYS} days on Google Drive..."

rclone delete ${DRY_RUN} \
    "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/" \
    --min-age "${GDRIVE_RETENTION_DAYS}d" \
    --include "*.sql.gz"

REMOTE_COUNT=$(rclone ls "${RCLONE_REMOTE}:${GDRIVE_FOLDER}/" --include "*.sql.gz" 2>/dev/null | wc -l)
echo "[$(date)] Google Drive retention: ${REMOTE_COUNT} backups remaining"

# ── Success notification ────────────────────────────────────────────────────
if [[ -x "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" ]]; then
    "${NOTIFY_SCRIPT_DIR}/notify_backup.sh" "SUCCESS" "Backup ${BACKUP_NAME} (${BACKUP_SIZE}) uploaded to Google Drive. ${REMOTE_COUNT} backups on GDrive."
fi

echo "[$(date)] Sync complete"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x backend/scripts/sync_backup_gdrive.sh
```

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/sync_backup_gdrive.sh
git commit -m "feat: add Google Drive backup sync script with retention and verification"
```

---

### Task 3: Create Email Notification Script

**Files:**
- Create: `backend/scripts/notify_backup.sh`

- [ ] **Step 1: Create the notification script**

Create `backend/scripts/notify_backup.sh`:

```bash
#!/bin/bash
# Send email notification about backup status
# Uses msmtp (lightweight SMTP client)
#
# Prerequisites:
#   - msmtp installed: apt install msmtp
#   - Config at /etc/msmtprc or ~/.msmtprc
#
# Usage: ./notify_backup.sh <STATUS> <MESSAGE>
#   STATUS: SUCCESS | FAILED | WARNING

set -euo pipefail

STATUS="${1:-UNKNOWN}"
MESSAGE="${2:-No details provided}"
RECIPIENT="${BACKUP_NOTIFY_EMAIL:-}"
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')

if [[ -z "${RECIPIENT}" ]]; then
    echo "[$(date)] NOTIFY: No BACKUP_NOTIFY_EMAIL set — skipping email"
    echo "[$(date)] NOTIFY: Status=${STATUS} Message=${MESSAGE}"
    exit 0
fi

# Choose subject prefix based on status
case "${STATUS}" in
    SUCCESS) SUBJECT_PREFIX="[OK]" ;;
    FAILED)  SUBJECT_PREFIX="[ALERT]" ;;
    WARNING) SUBJECT_PREFIX="[WARN]" ;;
    *)       SUBJECT_PREFIX="[INFO]" ;;
esac

SUBJECT="${SUBJECT_PREFIX} SSMSPL Backup — ${STATUS} — ${TIMESTAMP}"

# Send via msmtp
cat <<EOF | msmtp "${RECIPIENT}"
From: SSMSPL Backup <${BACKUP_NOTIFY_EMAIL}>
To: ${RECIPIENT}
Subject: ${SUBJECT}
Content-Type: text/plain; charset=UTF-8

SSMSPL Database Backup Report
=============================
Status:    ${STATUS}
Server:    ${HOSTNAME}
Time:      ${TIMESTAMP}
Details:   ${MESSAGE}

---
This is an automated notification from the SSMSPL backup system.
EOF

echo "[$(date)] NOTIFY: Email sent to ${RECIPIENT} — ${STATUS}"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x backend/scripts/notify_backup.sh
```

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/notify_backup.sh
git commit -m "feat: add backup email notification script via msmtp"
```

---

### Task 4: VPS Setup — Install rclone and msmtp

> **This task is manual — run these commands on the VPS via SSH.**

- [ ] **Step 1: Install rclone**

```bash
sudo apt update
sudo apt install -y rclone
rclone version   # verify installed
```

- [ ] **Step 2: Configure rclone with Google Drive**

This is interactive — must be done in an SSH session:

```bash
rclone config
```

Follow the prompts:
1. `n` — New remote
2. Name: `gdrive`
3. Storage type: `drive` (Google Drive)
4. Client ID: leave blank (uses rclone's default)
5. Client secret: leave blank
6. Scope: `1` (full access)
7. Root folder ID: leave blank
8. Service account file: leave blank
9. Auto config: `n` (since this is a headless server)
10. It will give you a URL — open it in your browser, authorize, paste the code back
11. Team drive: `n`
12. Confirm: `y`

Verify it works:

```bash
rclone lsd gdrive:          # should list your Google Drive folders
rclone mkdir gdrive:SSMSPL-Backups   # create the backup folder
```

- [ ] **Step 3: Install msmtp and configure for Gmail**

```bash
sudo apt install -y msmtp msmtp-mta
```

Create `/etc/msmtprc`:

```ini
# Gmail SMTP configuration for SSMSPL backup notifications
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /var/log/msmtp.log

account        gmail
host           smtp.gmail.com
port           587
from           YOUR_GMAIL@gmail.com
user           YOUR_GMAIL@gmail.com
password       YOUR_16_CHAR_APP_PASSWORD

account default : gmail
```

Secure the config:

```bash
sudo chmod 600 /etc/msmtprc
```

**To get a Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Linux Computer"
3. Copy the 16-character password
4. Paste it as the `password` value in `/etc/msmtprc`

Test it:

```bash
echo "Test from SSMSPL backup system" | msmtp YOUR_EMAIL@gmail.com
```

- [ ] **Step 4: Set environment variable for notification email**

Add to your shell profile or `/etc/environment`:

```bash
export BACKUP_NOTIFY_EMAIL="your-email@gmail.com"
```

---

### Task 5: Set Up Cron Job

- [ ] **Step 1: Create the cron entry**

```bash
sudo crontab -e
```

Add this line:

```cron
# SSMSPL: Upload daily DB backup to Google Drive (runs 15 min after backup_db.sh)
15 2 * * * BACKUP_DIR=/opt/ssmspl/backups BACKUP_NOTIFY_EMAIL=your-email@gmail.com /opt/ssmspl/backend/scripts/sync_backup_gdrive.sh >> /var/log/ssmspl-backup-sync.log 2>&1
```

> **Note:** Adjust `/opt/ssmspl` to wherever the repo lives on the VPS. The 15-minute offset gives `backup_db.sh` time to finish (a small DB dump takes seconds, but this provides margin).

- [ ] **Step 2: Create the log file with proper permissions**

```bash
sudo touch /var/log/ssmspl-backup-sync.log
sudo chmod 644 /var/log/ssmspl-backup-sync.log
```

- [ ] **Step 3: Verify cron is running**

```bash
sudo crontab -l   # should show the new entry
sudo systemctl status cron   # should be active
```

---

### Task 6: End-to-End Verification

- [ ] **Step 1: Test the backup pipeline manually**

```bash
# 1. Trigger a backup manually
docker exec ssmspl-db-backup-1 /scripts/backup_db.sh

# 2. Verify it landed in the bind mount
ls -lh ./backups/

# 3. Run the sync script manually
BACKUP_DIR=./backups BACKUP_NOTIFY_EMAIL=your-email@gmail.com ./backend/scripts/sync_backup_gdrive.sh

# 4. Check Google Drive
rclone ls gdrive:SSMSPL-Backups/
```

Expected:
- Backup file appears in `./backups/`
- Same file appears in Google Drive under `SSMSPL-Backups/`
- You receive a success email

- [ ] **Step 2: Test failure notification**

```bash
# Point at an empty directory to simulate "no backup found"
BACKUP_DIR=/tmp/empty-test BACKUP_NOTIFY_EMAIL=your-email@gmail.com ./backend/scripts/sync_backup_gdrive.sh
```

Expected: You receive a FAILED email saying "No backup files found".

- [ ] **Step 3: Test restore from Google Drive backup**

```bash
# Download a backup from Google Drive
rclone copy gdrive:SSMSPL-Backups/LATEST_BACKUP_NAME.sql.gz /tmp/restore-test/

# Verify it's valid (just check, don't actually restore to prod!)
gunzip -t /tmp/restore-test/LATEST_BACKUP_NAME.sql.gz
echo "Backup integrity: OK"
```

- [ ] **Step 4: Commit everything and document**

```bash
git add -A
git commit -m "feat: complete automated Google Drive backup system with notifications"
```

---

## Backup Schedule Summary

| Time | Action | Location |
|---|---|---|
| **2:00 AM** | `backup_db.sh` runs (Docker service) | `./backups/` on VPS |
| **2:15 AM** | `sync_backup_gdrive.sh` runs (host cron) | Google Drive `SSMSPL-Backups/` |
| **2:15 AM** | Email notification sent | Your inbox |

## Retention Policy

| Location | Retention | Managed By |
|---|---|---|
| VPS (`./backups/`) | 7 days | `backup_db.sh` (existing) |
| Google Drive | 30 days | `sync_backup_gdrive.sh` (rclone) |

## Restore Procedure

To restore from a Google Drive backup:

```bash
# 1. List available backups
rclone ls gdrive:SSMSPL-Backups/

# 2. Download the backup you want
rclone copy gdrive:SSMSPL-Backups/ssmspl_db_prod_20260402_020000.sql.gz ./backups/

# 3. Restore (uses the existing restore script)
docker exec -i ssmspl-db-backup-1 /scripts/restore_db.sh /backups/ssmspl_db_prod_20260402_020000.sql.gz
```

## Hostinger VPS Snapshots (Bonus)

In addition to automated DB backups, take periodic full VPS snapshots from the Hostinger panel:

1. Log into Hostinger VPS dashboard
2. Go to **Snapshots** section
3. Create a manual snapshot weekly (or before any major deployment)
4. Hostinger allows 1-3 snapshots depending on plan — rotate them

This covers the **entire server state** (OS, Docker, config, certs, etc.), not just the database.
