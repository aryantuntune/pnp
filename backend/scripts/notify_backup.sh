#!/bin/bash
# Send email notification about backup status
# Uses msmtp (lightweight SMTP client)
#
# Prerequisites:
#   - msmtp installed: apt install msmtp msmtp-mta
#   - Config at /etc/msmtprc with Gmail SMTP credentials
#
# Usage: ./notify_backup.sh <STATUS> <MESSAGE>
#   STATUS: SUCCESS | FAILED | WARNING

set -euo pipefail

STATUS="${1:-UNKNOWN}"
MESSAGE="${2:-No details provided}"
BACKUP_DIR="${BACKUP_DIR:-/var/www/ssmspl/backups}"
SERVER_HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')

# ── Check msmtp is installed ──────────────────────────────────────────────
if ! command -v msmtp &>/dev/null; then
    echo "[$(date)] NOTIFY: msmtp not installed — cannot send email"
    echo "[$(date)] NOTIFY: Status=${STATUS} Message=${MESSAGE}"
    echo "[$(date)] NOTIFY: Install msmtp: apt install msmtp msmtp-mta"
    exit 0
fi

# ── Build recipient list: env var + .notify_emails file from backend DB ───
RECIPIENTS=""
if [[ -n "${BACKUP_NOTIFY_EMAIL:-}" ]]; then
    RECIPIENTS="${BACKUP_NOTIFY_EMAIL}"
fi
NOTIFY_FILE="${BACKUP_DIR}/.notify_emails"
if [[ -f "${NOTIFY_FILE}" ]]; then
    while IFS= read -r email; do
        [[ -z "${email}" ]] && continue
        if [[ -z "${RECIPIENTS}" ]]; then
            RECIPIENTS="${email}"
        else
            # Avoid duplicates
            echo "${RECIPIENTS}" | grep -qF "${email}" || RECIPIENTS="${RECIPIENTS} ${email}"
        fi
    done < "${NOTIFY_FILE}"
fi

if [[ -z "${RECIPIENTS}" ]]; then
    echo "[$(date)] NOTIFY: No recipients configured — skipping email"
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

# Send to each recipient
for RECIPIENT in ${RECIPIENTS}; do
    if cat <<EOF | msmtp "${RECIPIENT}"; then
To: ${RECIPIENT}
Subject: ${SUBJECT}
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8

SSMSPL Database Backup Report
=============================
Status:    ${STATUS}
Server:    ${SERVER_HOSTNAME}
Time:      ${TIMESTAMP}
Details:   ${MESSAGE}

---
This is an automated notification from the SSMSPL backup system.
EOF
        echo "[$(date)] NOTIFY: Email sent to ${RECIPIENT} — ${STATUS}"
    else
        echo "[$(date)] NOTIFY: WARNING — Failed to send email to ${RECIPIENT} (msmtp returned $?)"
    fi
done
