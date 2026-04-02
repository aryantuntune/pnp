# User Session Monitor — Design Spec

**Date**: 2026-04-02
**Feature**: Real-time + historical user session monitoring for SUPER_ADMIN
**Status**: Approved

---

## Overview

A SUPER_ADMIN-only dashboard page that shows:
- **Live view**: Who is currently online, their role, IP/city, session duration, and ticket stats (for billing operators and checkers).
- **Historical view**: Past sessions with login/logout times, active duration, end reason, IP/city, and ticket totals.

## Data Model

### New table: `user_sessions`

| Column | Type | Description |
|---|---|---|
| `id` | BIGINT PK (auto-increment) | Row ID |
| `user_id` | UUID FK → users(id) | The user this session belongs to |
| `session_id` | VARCHAR(36) NOT NULL | Matches `users.active_session_id` at creation time |
| `started_at` | TIMESTAMPTZ NOT NULL | Set on login |
| `ended_at` | TIMESTAMPTZ NULL | Set on logout/timeout; NULL = session is active |
| `last_heartbeat` | TIMESTAMPTZ NOT NULL | Updated every 30s by existing `get_current_user` throttle |
| `end_reason` | VARCHAR(20) NULL | One of: `logout`, `timeout`, `login_elsewhere` |
| `ip_address` | VARCHAR(45) NULL | Client IP captured at login (supports IPv6) |
| `city` | VARCHAR(100) NULL | Resolved from IP at login via ip-api.com |
| `user_agent` | VARCHAR(255) NULL | Browser/device info from request headers |

**Indexes:**
- `idx_user_sessions_user_id` on `(user_id)`
- `idx_user_sessions_ended_at` on `(ended_at)` — fast lookup of active sessions (`WHERE ended_at IS NULL`)
- `idx_user_sessions_started_at` on `(started_at DESC)` — history queries sorted by recency

**Active session**: `ended_at IS NULL`
**Session duration**: `COALESCE(ended_at, now()) - started_at`

## Backend Changes

### 1. Model: `app/models/user_session.py`

New SQLAlchemy model mapping to `user_sessions` table. No AuditMixin (this table has its own timestamps).

### 2. Service: `app/services/user_session_service.py`

Functions:
- `start_session(db, user_id, session_id, ip_address, user_agent)` — Creates row, triggers async IP geolocation.
- `end_session(db, session_id, reason)` — Sets `ended_at = now()` and `end_reason`.
- `update_heartbeat(db, session_id)` — Updates `last_heartbeat`.
- `close_stale_sessions(db)` — Finds sessions where `ended_at IS NULL AND last_heartbeat < now() - 5 minutes`, sets `ended_at = last_heartbeat`, `end_reason = 'timeout'`. Called lazily on read endpoints.
- `get_active_sessions(db)` — Returns active sessions joined with user info and ticket counts.
- `get_session_history(db, date_from, date_to, user_id_filter, skip, limit)` — Paginated history with filters.

### 3. IP Geolocation: `app/services/geo_service.py`

- Calls `http://ip-api.com/json/{ip}?fields=city,regionName,country` using `httpx.AsyncClient`.
- 45 requests/minute free tier — more than enough for login events.
- Fail-safe: returns `None` on error, timeout (2s), or private/localhost IPs.
- No caching needed — one lookup per login.

### 4. Auth Service Integration

**`auth_service.login()`** — after successful auth:
- Call `user_session_service.start_session()` with IP from `request.client.host` and `request.headers.get("user-agent")`.

**`auth_service._start_session()`** — when overwriting an existing session:
- Call `user_session_service.end_session(old_session_id, reason='login_elsewhere')` before generating new session ID.

**`auth_service.logout()`** — on explicit logout:
- Call `user_session_service.end_session(session_id, reason='logout')`.

### 5. Heartbeat Integration

**`dependencies.get_current_user()`** — in the existing 30-second throttle block (lines 78-81):
- Also call `user_session_service.update_heartbeat(db, user.active_session_id)`.
- This is a single UPDATE, same transaction as the existing `session_last_active` write.

### 6. Router: `app/routers/user_sessions.py`

**`GET /api/user-sessions/active`**
- SUPER_ADMIN only.
- Calls `close_stale_sessions()` first (lazy timeout cleanup).
- Returns list of active sessions with user info and ticket counts.

**`GET /api/user-sessions/history`**
- SUPER_ADMIN only.
- Query params: `date_from`, `date_to`, `user_id` (optional filter), `skip`, `limit`.
- Returns paginated session history with ticket counts.

**`GET /api/user-sessions/history/count`**
- SUPER_ADMIN only.
- Returns total count for pagination.

### 7. Ticket Counts (computed on-the-fly)

For billing operators (tickets generated):
```sql
SELECT COUNT(*) FROM tickets
WHERE created_by = :user_id
  AND created_at BETWEEN :started_at AND COALESCE(:ended_at, now())
```

For ticket checkers (tickets verified):
```sql
SELECT COUNT(*) FROM tickets
WHERE status = 'VERIFIED'
  AND checked_in_at BETWEEN :started_at AND COALESCE(:ended_at, now())
```

Note: Ticket checker verification attribution — `checked_in_at` timestamp indicates when verification happened, but there's no `verified_by` column. We'll use `updated_by` as the checker's user ID (since verification is the last update on a ticket).

Ticket counts are only computed for `BILLING_OPERATOR` and `TICKET_CHECKER` roles. For other roles, the field is omitted/null.

### 8. RBAC Integration

Add `"User Sessions"` to `ROLE_MENU_ITEMS[UserRole.SUPER_ADMIN]` in `core/rbac.py`.

## Frontend

### Page: `/dashboard/user-sessions`

SUPER_ADMIN only. Two tabs:

**Tab 1: Live Sessions**
- Refresh button (manual, no auto-polling).
- Table columns: #, User (full name), Role, IP / City, Login Time, Duration (computed: `now - started_at`), Tickets (for billing ops/checkers only, blank for others).
- Active session rows show a green dot indicator.
- Empty state: "No active sessions."

**Tab 2: Session History**
- Filters: Date range picker (from/to), User dropdown (optional).
- Paginated table columns: #, User, Role, Login, Logout, Duration, End Reason (badge: green for logout, yellow for timeout, red for login_elsewhere), IP / City, Tickets.
- Pagination: 20 rows per page with count.

### Sidebar

Map `"User Sessions"` string (from `menu_items`) to route `/dashboard/user-sessions` with an appropriate icon (e.g., `Users` or `Activity` from lucide-react).

## Migration

Alembic migration to create `user_sessions` table with indexes. DDL script updated with CREATE TABLE + PATCH section.

## Constraints & Edge Cases

- **Private IPs / localhost**: Geolocation returns null city — display "Local" or just the IP.
- **ip-api.com down**: City is null, session still created. No retry.
- **Multiple rapid logins**: Each login closes the previous session (`login_elsewhere`) and starts a new one. At most one active session per user.
- **Server restart**: Sessions that were active before restart will have stale heartbeats. Next SUPER_ADMIN page load triggers `close_stale_sessions()` which cleans them up with `end_reason = 'timeout'`.
- **Retention**: No auto-purge. Sessions accumulate. Can add retention policy later if table grows large.
