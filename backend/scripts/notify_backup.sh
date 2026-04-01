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
RECIPIENT="${BACKUP_NOTIFY_EMAIL:-}"
SERVER_HOSTNAME=$(hostname)
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
