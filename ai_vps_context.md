# AI Assistant VPS Operations & System Architecture Blueprint

This document serves as the absolute master "System Prompt" and operational manual for any AI assistant tasked with managing, debugging, or deploying to the SSMSPL production VPS. 

By ingesting this file, an AI will instantly understand the exact infrastructure state, tech stack, database configurations, and strict execution protocols required to write flawless, copy-paste-ready commands for this server.

> [!CAUTION]
> **SECURITY NOTICE:** Real production passwords (such as email SMTP passwords, Razorpay Live keys, JWT secrets, or the raw QZ private key file) are **never** to be written in this document or committed to Git. They exist strictly on the VPS in `/var/www/ssmspl/backend/.env.production`. The usernames and passwords shown below represent the Docker-layer default database connectivity configurations.

---

## 1. Full Technology Stack

* **Backend Framework:** Python FastAPI (managed by Gunicorn with `preload_app=True` to share memory state like `build_id`).
* **Frontend Framework:** Next.js (React), running inside a Node.js container.
* **Database Engine:** PostgreSQL 16.6 (Alpine).
* **Caching & Rate Limiting:** Redis 7.4 (Alpine), integrated with Fastapi `slowapi` rate limiter.
* **Web Server & Reverse Proxy:** Nginx 1.27 (Alpine).
* **Automated SSL:** Certbot (Let's encrypt).
* **Background Jobs / DB Backups:** Custom Alpine Postgres container executing `backup_db.sh` triggered at 02:00 AM IST, synchronized to Google Drive via `rclone`.

---

## 2. Server Infrastructure & Paths

* **Server OS Environment**: Linux VPS accessed via SSH.
* **Primary SSH User**: `jetty_admin`
* **Root Project Directory**: `/var/www/ssmspl`
* **Orchestrator**: Docker Compose (V2) using the filename: `docker-compose.prod.yml`.

### Docker Architecture Map
The server manages exactly **7** interdependent services via Docker Compose:
1. `backend` (Port 8000 internal)
2. `frontend` (Port 3000 internal)
3. `nginx` (Ports 80/443 exposed to the public)
4. `db` (PostgreSQL - completely isolated on Docker's `internal` network)
5. `redis` (Redis - completely isolated on Docker's `internal` network)
6. `db-backup` (Runs cron loop, mounts `/backups` to the host)
7. `certbot` (Runs renewal loops every 12 hours)

---

## 3. Database & System Configurations

Because the services run isolated in Docker, they rely on exact usernames and passwords mapped via environment variables to connect to each other internally.

### PostgreSQL (Internal Docker DNS: `db:5432`)
* **Database Name:** `ssmspl_db_prod`
* **Username:** `ssmspl_user`
* **Password:** `ssmspl_prod_pass`
* **Connection String:** `postgresql+asyncpg://ssmspl_user:ssmspl_prod_pass@db:5432/ssmspl_db_prod`

### Redis (Internal Docker DNS: `redis:6379`)
* **Password:** `ssmspl_redis_prod`
* **Storage Allocation:** DB 0 is used for general cache, DB 1 is used for rate limiting storage.

---

## 4. Notable Infrastructure "Quirks" & Patches

An AI must be aware of these fundamental design implementations that were custom-built to solve production edge cases:

1. **Nginx DNS Resolution Fix:** Nginx routes traffic dynamically via `resolver 127.0.0.11 valid=10s`. Do **not** use static `upstream` blocks. We use `proxy_pass $backend_up` so Nginx never permanently caches old Docker container IPs when containers restart.
2. **QZ Tray Silent Printing:** Printing relies on `public/ssmspl-qz.crt` for frontend authentication, and the backend signs print requests securely using `QZ_PRIVATE_KEY_PEM` stored in `.env.production`.
3. **Timezone Discrepancy Matrix (CRITICAL):**
   * The Docker containers execute natively in **UTC**.
   * The business logic strictly requires **IST (Asia/Kolkata)**.
   * **Python Data:** Do not use `date.today()`. Exclusively use our custom `app.core.timezone.today_ist()` fallback.
   * **SQL Data:** When querying raw creation times in PostgreSQL, the AI **must** dynamically cast it: `(created_at AT TIME ZONE 'Asia/Kolkata')`.

---

## 5. Strict Command Execution Rules

Because the app is deeply containerized, **never** give native Linux service commands (e.g., `systemctl restart postgresql`). 
All interactions must be routed through Docker Compose.

### Safe Container Rebuilding
```bash
docker compose -f docker-compose.prod.yml up -d --build backend frontend
```

### Viewing Logs (Crucial for Debugging)
Never use `cat` on log files inside containers. Use safe trailing Docker logs:
* `docker compose -f docker-compose.prod.yml logs --tail=100 backend`
* `docker compose -f docker-compose.prod.yml logs --tail=50 nginx`
* `docker compose -f docker-compose.prod.yml logs --tail=50 redis`

---

## 6. SQL Patching & Database Query Syntax Standard

When an AI must generate raw SQL scripts to query or patch production data, the command must be perfectly formatted for the Bash terminal to prevent syntax errors:

### The Execution Wrapper
```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U ssmspl_user -d ssmspl_db_prod -c "
SELECT * FROM tickets LIMIT 5;
"
```
> [!IMPORTANT]
> Always use the `-T` flag combined with `exec` when giving the user queries. This disables TTY allocation, ensuring multi-line queries pipeline cleanly without hanging the SSH terminal.

### String Interpolation Rules
* Always wrap the entire outer SQL block in **Double Quotes** (`"`).
* Inside the actual SQL block, safely use **Single Quotes** (`'`) for dates strings, timezones, and text to prevent Bash from parsing variables and breaking the payload.

---

## 7. Operational Workflow Between Fast-Paced Users and AIs

To maximize efficiency and eliminate fatal errors on the live server, follow this conversational loop:

1. **Diagnostics First:** When the user presents an error (e.g. 502 Bad Gateway), the AI drops all assumptions and provides exact `docker logs` commands to extract the active traceback.
2. **Database Migrations:** The AI must proactively realize when an Alembic migration is required. If the user commits backend schema changes using `git pull origin main`, the AI **must** instruct the execution of `... exec backend alembic upgrade head` immediately after the containers boot.
3. **Data Mutation Safety Loop:** If the user requests an `UPDATE` or `DELETE` fix directly to the Postgres database, the AI **must** first provide a `SELECT preview` command. The user is required to visually verify the count and affected rows before the AI constructs the final irreversible `UPDATE` command.
