# AI Assistant VPS Operations Blueprint

This document serves as the "System Prompt" and operational context for any AI assistant tasked with managing, debugging, or deploying to the SSMSPL production VPS. 

By providing this file to an AI, it will instantly understand the exact infrastructure state and syntax requirements needed to write safe, copy-paste-ready commands for this specific server.

---

## 1. Core Infrastructure Context

* **Server OS Environment**: Linux VPS accessed via SSH (`jetty_admin`).
* **Root Project Directory**: `/var/www/ssmspl`
* **Orchestrator**: Docker Compose (V2) using a custom filename: `docker-compose.prod.yml`.
* **Services Defined**:
  * `backend` (FastAPI + Gunicorn)
  * `frontend` (Next.js)
  * `nginx` (Reverse Proxy)
  * `db` (Postgres 16.6 Alpine)
  * `redis` (Rate Limit Storage)
  * `db-backup` (Scheduled Postgres Dumps)
  * `certbot` (Let's Encrypt SSL)

---

## 2. Strict Command Execution Rules

Because the app runs inside Docker Compose, **never** give native Linux service commands (e.g., `systemctl restart postgresql`)! 
All commands must be explicitly routed through Docker.

### Running Backend/Frontend Commands
* **Correct**: `docker compose -f docker-compose.prod.yml exec backend alembic upgrade head`
* **Incorrect**: `alembic upgrade head`

### Viewing Logs (Crucial for Debugging)
Never use `cat` on log files inside containers if Docker captures them. Use safe trailing logs:
* **Backend Errors**: `docker compose -f docker-compose.prod.yml logs --tail=100 backend`
* **Nginx Errors**: `docker compose -f docker-compose.prod.yml logs --tail=50 nginx`

---

## 3. Database Interaction (SQL) Syntax Rules

When providing the user with raw SQL scripts to query or patch production data, the command must be perfectly formatted for the Bash terminal to prevent syntax errors:

1. **The Execution Wrapper**: 
   `docker compose -f docker-compose.prod.yml exec -T db psql -U ssmspl_user -d ssmspl_db_prod -c "..."`
   * *Note the `-T` flag*: This disables TTY allocation, ensuring multi-line queries run cleanly without hanging the terminal.
2. **String Interpolation Rules**:
   * Wrap the entire SQL block in **Double Quotes** (`"`).
   * Inside the SQL block, exclusively use **Single Quotes** (`'`) for dates strings, timezones, and text to prevent Bash from breaking the command.
3. **Timezone Awareness**:
   * Server database stores timestamps in UTC.
   * India Standard Time (IST) requires explicit conversion during queries using: `(created_at AT TIME ZONE 'Asia/Kolkata')`.

---

## 4. The Standard Deployment Sequence

When code is pushed to GitHub (`origin/main`), the AI should provide this exact sequence to physically deploy it, intelligently appending the Database Migration step ONLY if the codebase history shows Alembic files altered.

```bash
cd /var/www/ssmspl
git pull origin main

# 1. Rebuild and restart affected containers
docker compose -f docker-compose.prod.yml up -d --build backend frontend

# 2. OPTIONAL (AI must determine if schema changed):
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## 5. How User and AI Should Best Communicate

To maximize efficiency and eliminate fatal errors (like dropped data), follow this conversational loop:

1. **User Goal**: State the symptom (e.g., "502 Bad Gateway completely breaking mobile app").
2. **AI Action**: Do not guess! Provide exact `logs` or `ps` commands from Section 2 to gather diagnostics.
3. **User Action**: Copy-paste the raw terminal output back into the chat.
4. **AI Action**: Analyze the stack trace. If it's a code bug (e.g., Missing python dependency, DB Timezone error), write the fix in the IDE directly, instruct the user to deploy, and provide the exact Phase 4 command block.
5. **Data Mutations**: If running raw SQL updates against production, the AI **must** first provide a `SELECT preview` command, requesting the user verify it isolated the exact correct rows BEFORE providing the final `UPDATE` command.
