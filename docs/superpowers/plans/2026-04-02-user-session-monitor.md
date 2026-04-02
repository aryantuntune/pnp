# User Session Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a SUPER_ADMIN-only dashboard page showing live active sessions and historical session logs with IP/city, durations, and ticket counts for billing operators/checkers.

**Architecture:** New `user_sessions` table tracks each login→logout lifecycle. Login creates a row, logout/timeout/login-elsewhere closes it. Heartbeat (existing 30s throttle) updates `last_heartbeat`. Stale sessions (no heartbeat for 5 min) are lazily closed on read. IP geolocation resolved at login via ip-api.com. Frontend has two tabs: Live Sessions + Session History.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, httpx (geo lookup), Next.js, TypeScript, Tailwind CSS, DataTable component.

---

## File Structure

### Backend — New files
| File | Responsibility |
|---|---|
| `backend/app/models/user_session.py` | SQLAlchemy model for `user_sessions` table |
| `backend/app/schemas/user_session.py` | Pydantic response schemas |
| `backend/app/services/user_session_service.py` | Session CRUD, stale cleanup, ticket count queries |
| `backend/app/services/geo_service.py` | IP → city resolution via ip-api.com |
| `backend/app/routers/user_sessions.py` | API endpoints (SUPER_ADMIN only) |
| `backend/alembic/versions/a1b2c3d4e5f6_create_user_sessions_table.py` | Migration |

### Backend — Modified files
| File | Change |
|---|---|
| `backend/app/services/auth_service.py` | Call session service on login, logout, login-elsewhere |
| `backend/app/routers/auth.py` | Pass `request` to login service for IP/user-agent |
| `backend/app/dependencies.py` | Update heartbeat in session table alongside existing throttle |
| `backend/app/core/rbac.py` | Add "User Sessions" to SUPER_ADMIN menu |
| `backend/app/main.py` | Register new router |
| `backend/scripts/ddl.sql` | Add `user_sessions` CREATE TABLE + PATCH |

### Frontend — New files
| File | Responsibility |
|---|---|
| `frontend/src/app/dashboard/user-sessions/page.tsx` | Full page with two tabs |
| `frontend/src/types/user-session.ts` | TypeScript interfaces |

### Frontend — Modified files
| File | Change |
|---|---|
| `frontend/src/components/Sidebar.tsx` | Add route mapping for "User Sessions" |

---

## Task 1: Database model and migration

**Files:**
- Create: `backend/app/models/user_session.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/a1b2c3d4e5f6_create_user_sessions_table.py`
- Modify: `backend/scripts/ddl.sql`

- [ ] **Step 1: Create the SQLAlchemy model**

Create `backend/app/models/user_session.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    end_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<UserSession id={self.id} user_id={self.user_id} session_id={self.session_id}>"
```

- [ ] **Step 2: Register model in `__init__.py`**

Add to `backend/app/models/__init__.py`:

```python
from app.models.user_session import UserSession
```

And add `"UserSession"` to the `__all__` list.

- [ ] **Step 3: Create Alembic migration**

Create `backend/alembic/versions/a1b2c3d4e5f6_create_user_sessions_table.py`:

```python
"""create user_sessions table

Revision ID: a1b2c3d4e5f6
Revises: f7b2c5d84a36
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f7b2c5d84a36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('end_reason', sa.String(20), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
    )
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_ended_at', 'user_sessions', ['ended_at'])
    op.create_index('idx_user_sessions_started_at', 'user_sessions', ['started_at'])


def downgrade() -> None:
    op.drop_table('user_sessions')
```

- [ ] **Step 4: Update DDL script**

Add to `backend/scripts/ddl.sql` — in the TABLES section (after `daily_report_recipients`):

```sql
-- User sessions table (tracks login/logout lifecycle for monitoring)
CREATE TABLE IF NOT EXISTS user_sessions (
    id                  BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id          VARCHAR(36) NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at            TIMESTAMPTZ,
    last_heartbeat      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_reason          VARCHAR(20),
    ip_address          VARCHAR(45),
    city                VARCHAR(100),
    user_agent          VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_ended_at ON user_sessions(ended_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_started_at ON user_sessions(started_at);
```

- [ ] **Step 5: Run migration and verify**

```bash
cd backend
python -m alembic upgrade head
```

Verify table exists:
```bash
python -c "
import asyncio
async def check():
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.models.user_session import UserSession
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(func.count()).select_from(UserSession))
        print('user_sessions OK, rows:', r.scalar())
asyncio.run(check())
"
```

Expected: `user_sessions OK, rows: 0`

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/user_session.py backend/app/models/__init__.py backend/alembic/versions/a1b2c3d4e5f6_create_user_sessions_table.py backend/scripts/ddl.sql
git commit -m "feat: add user_sessions table for session monitoring"
```

---

## Task 2: Geo service (IP → city)

**Files:**
- Create: `backend/app/services/geo_service.py`

- [ ] **Step 1: Create geo service**

Create `backend/app/services/geo_service.py`:

```python
import logging
from ipaddress import ip_address as parse_ip

import httpx

logger = logging.getLogger("ssmspl")

_PRIVATE_PREFIXES = ("127.", "10.", "172.", "192.168.", "0.", "::1", "fd", "fe80")


async def resolve_city(ip: str | None) -> str | None:
    """Resolve an IP address to a city name via ip-api.com.

    Returns None on error, timeout, or private/localhost IPs.
    Free tier: 45 requests/minute — more than enough for login events.
    """
    if not ip:
        return None

    # Skip private/loopback IPs
    if any(ip.startswith(p) for p in _PRIVATE_PREFIXES):
        return None

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,city,regionName,country"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("status") != "success":
                return None
            parts = [data.get("city"), data.get("regionName"), data.get("country")]
            return ", ".join(p for p in parts if p) or None
    except Exception as exc:
        logger.debug("Geo lookup failed for %s: %s", ip, exc)
        return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/geo_service.py
git commit -m "feat: add geo_service for IP-to-city resolution"
```

---

## Task 3: User session service

**Files:**
- Create: `backend/app/services/user_session_service.py`

- [ ] **Step 1: Create the service**

Create `backend/app/services/user_session_service.py`:

```python
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update as sa_update, case, and_

from app.models.user_session import UserSession
from app.models.user import User
from app.models.ticket import Ticket
from app.core.rbac import UserRole
from app.services.geo_service import resolve_city

STALE_TIMEOUT = timedelta(minutes=5)


async def start_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> UserSession:
    """Create a new session row. City is resolved async from IP."""
    city = await resolve_city(ip_address)
    now = datetime.now(timezone.utc)
    session = UserSession(
        user_id=user_id,
        session_id=session_id,
        started_at=now,
        last_heartbeat=now,
        ip_address=ip_address,
        city=city,
        user_agent=user_agent[:255] if user_agent and len(user_agent) > 255 else user_agent,
    )
    db.add(session)
    return session


async def end_session(
    db: AsyncSession,
    session_id: str,
    reason: str,
) -> None:
    """Close an active session by session_id."""
    now = datetime.now(timezone.utc)
    await db.execute(
        sa_update(UserSession)
        .where(
            UserSession.session_id == session_id,
            UserSession.ended_at.is_(None),
        )
        .values(ended_at=now, end_reason=reason)
    )


async def update_heartbeat(db: AsyncSession, session_id: str) -> None:
    """Update last_heartbeat for the active session."""
    now = datetime.now(timezone.utc)
    await db.execute(
        sa_update(UserSession)
        .where(
            UserSession.session_id == session_id,
            UserSession.ended_at.is_(None),
        )
        .values(last_heartbeat=now)
    )


async def close_stale_sessions(db: AsyncSession) -> int:
    """Close sessions with no heartbeat for >5 minutes. Returns count closed."""
    cutoff = datetime.now(timezone.utc) - STALE_TIMEOUT
    result = await db.execute(
        sa_update(UserSession)
        .where(
            UserSession.ended_at.is_(None),
            UserSession.last_heartbeat < cutoff,
        )
        .values(ended_at=UserSession.last_heartbeat, end_reason="timeout")
    )
    await db.commit()
    return result.rowcount


def _ticket_count_subquery(user_id_col, started_at_col, ended_at_col, role_col):
    """Build a correlated subquery for ticket counts based on role."""
    # For BILLING_OPERATOR: tickets created during session
    billing_count = (
        select(func.count())
        .where(
            Ticket.created_by == user_id_col,
            Ticket.created_at >= started_at_col,
            Ticket.created_at <= func.coalesce(ended_at_col, func.now()),
        )
        .correlate(UserSession)
        .scalar_subquery()
    )
    # For TICKET_CHECKER: tickets verified during session
    checker_count = (
        select(func.count())
        .where(
            Ticket.status == "VERIFIED",
            Ticket.updated_by == user_id_col,
            Ticket.checked_in_at >= started_at_col,
            Ticket.checked_in_at <= func.coalesce(ended_at_col, func.now()),
        )
        .correlate(UserSession)
        .scalar_subquery()
    )
    return case(
        (role_col == UserRole.BILLING_OPERATOR.value, billing_count),
        (role_col == UserRole.TICKET_CHECKER.value, checker_count),
        else_=None,
    )


async def get_active_sessions(db: AsyncSession) -> list[dict]:
    """Return all active sessions with user info and ticket counts."""
    ticket_count = _ticket_count_subquery(
        User.id, UserSession.started_at, UserSession.ended_at, User.role
    )
    query = (
        select(
            UserSession.id,
            UserSession.user_id,
            UserSession.session_id,
            UserSession.started_at,
            UserSession.last_heartbeat,
            UserSession.ip_address,
            UserSession.city,
            UserSession.user_agent,
            User.full_name,
            User.username,
            User.role,
            ticket_count.label("ticket_count"),
        )
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.ended_at.is_(None))
        .order_by(UserSession.started_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "id": row.id,
            "user_id": str(row.user_id),
            "session_id": row.session_id,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "last_heartbeat": row.last_heartbeat.isoformat() if row.last_heartbeat else None,
            "ip_address": row.ip_address,
            "city": row.city,
            "user_agent": row.user_agent,
            "full_name": row.full_name,
            "username": row.username,
            "role": row.role.value if hasattr(row.role, "value") else row.role,
            "ticket_count": row.ticket_count,
        }
        for row in rows
    ]


async def get_session_history(
    db: AsyncSession,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id_filter: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[dict]:
    """Return paginated session history with user info and ticket counts."""
    ticket_count = _ticket_count_subquery(
        User.id, UserSession.started_at, UserSession.ended_at, User.role
    )
    query = (
        select(
            UserSession.id,
            UserSession.user_id,
            UserSession.session_id,
            UserSession.started_at,
            UserSession.ended_at,
            UserSession.last_heartbeat,
            UserSession.end_reason,
            UserSession.ip_address,
            UserSession.city,
            UserSession.user_agent,
            User.full_name,
            User.username,
            User.role,
            ticket_count.label("ticket_count"),
        )
        .join(User, User.id == UserSession.user_id)
    )
    if date_from:
        query = query.where(UserSession.started_at >= date_from)
    if date_to:
        query = query.where(UserSession.started_at <= date_to)
    if user_id_filter:
        query = query.where(UserSession.user_id == user_id_filter)

    query = query.order_by(UserSession.started_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "id": row.id,
            "user_id": str(row.user_id),
            "session_id": row.session_id,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "ended_at": row.ended_at.isoformat() if row.ended_at else None,
            "last_heartbeat": row.last_heartbeat.isoformat() if row.last_heartbeat else None,
            "end_reason": row.end_reason,
            "ip_address": row.ip_address,
            "city": row.city,
            "user_agent": row.user_agent,
            "full_name": row.full_name,
            "username": row.username,
            "role": row.role.value if hasattr(row.role, "value") else row.role,
            "ticket_count": row.ticket_count,
        }
        for row in rows
    ]


async def count_session_history(
    db: AsyncSession,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id_filter: uuid.UUID | None = None,
) -> int:
    """Count total sessions matching filters (for pagination)."""
    query = select(func.count()).select_from(UserSession)
    if date_from:
        query = query.where(UserSession.started_at >= date_from)
    if date_to:
        query = query.where(UserSession.started_at <= date_to)
    if user_id_filter:
        query = query.where(UserSession.user_id == user_id_filter)
    result = await db.execute(query)
    return result.scalar() or 0
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/user_session_service.py
git commit -m "feat: add user_session_service with CRUD and ticket counts"
```

---

## Task 4: Pydantic schemas

**Files:**
- Create: `backend/app/schemas/user_session.py`

- [ ] **Step 1: Create schemas**

Create `backend/app/schemas/user_session.py`:

```python
from datetime import datetime

from pydantic import BaseModel, Field


class ActiveSessionRead(BaseModel):
    id: int = Field(..., description="Session row ID")
    user_id: str = Field(..., description="User UUID")
    session_id: str = Field(..., description="Session UUID")
    started_at: str | None = Field(None, description="Session start ISO timestamp")
    last_heartbeat: str | None = Field(None, description="Last heartbeat ISO timestamp")
    ip_address: str | None = Field(None, description="Client IP address")
    city: str | None = Field(None, description="City resolved from IP")
    user_agent: str | None = Field(None, description="Browser user-agent string")
    full_name: str = Field(..., description="User full name")
    username: str = Field(..., description="Username")
    role: str = Field(..., description="User role")
    ticket_count: int | None = Field(None, description="Tickets generated/verified during session (billing ops/checkers only)")


class SessionHistoryRead(ActiveSessionRead):
    ended_at: str | None = Field(None, description="Session end ISO timestamp")
    end_reason: str | None = Field(None, description="How session ended: logout, timeout, login_elsewhere")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/user_session.py
git commit -m "feat: add user_session Pydantic schemas"
```

---

## Task 5: API router

**Files:**
- Create: `backend/app/routers/user_sessions.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the router**

Create `backend/app/routers/user_sessions.py`:

```python
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_roles
from app.core.rbac import UserRole
from app.models.user import User
from app.schemas.user_session import ActiveSessionRead, SessionHistoryRead
from app.services import user_session_service

router = APIRouter(prefix="/api/user-sessions", tags=["User Sessions"])

_super_admin_only = require_roles(UserRole.SUPER_ADMIN)


@router.get(
    "/active",
    response_model=list[ActiveSessionRead],
    summary="List active user sessions",
    description="Returns all currently active sessions with user info and ticket counts. SUPER_ADMIN only.",
)
async def list_active_sessions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_super_admin_only),
):
    await user_session_service.close_stale_sessions(db)
    return await user_session_service.get_active_sessions(db)


@router.get(
    "/history",
    response_model=list[SessionHistoryRead],
    summary="List session history",
    description="Paginated session history with optional date and user filters. SUPER_ADMIN only.",
)
async def list_session_history(
    date_from: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: str | None = Query(None, description="Filter by user UUID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_super_admin_only),
):
    parsed_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc) if date_from else None
    parsed_to = (
        datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        if date_to
        else None
    )
    parsed_user_id = uuid.UUID(user_id) if user_id else None
    return await user_session_service.get_session_history(
        db, parsed_from, parsed_to, parsed_user_id, skip, limit,
    )


@router.get(
    "/history/count",
    response_model=int,
    summary="Count session history records",
    description="Total count for pagination. SUPER_ADMIN only.",
)
async def count_session_history(
    date_from: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: str | None = Query(None, description="Filter by user UUID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_super_admin_only),
):
    parsed_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc) if date_from else None
    parsed_to = (
        datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        if date_to
        else None
    )
    parsed_user_id = uuid.UUID(user_id) if user_id else None
    return await user_session_service.count_session_history(
        db, parsed_from, parsed_to, parsed_user_id,
    )


@router.get(
    "/users",
    summary="List users for filter dropdown",
    description="Returns id + full_name of all users. SUPER_ADMIN only.",
)
async def list_users_for_filter(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_super_admin_only),
):
    from sqlalchemy import select
    from app.models.user import User as UserModel
    result = await db.execute(
        select(UserModel.id, UserModel.full_name, UserModel.username, UserModel.role)
        .where(UserModel.is_active == True)
        .order_by(UserModel.full_name)
    )
    return [
        {
            "id": str(row.id),
            "full_name": row.full_name,
            "username": row.username,
            "role": row.role.value if hasattr(row.role, "value") else row.role,
        }
        for row in result.all()
    ]
```

- [ ] **Step 2: Register router in `main.py`**

In `backend/app/main.py`, add alongside other router imports:

```python
from app.routers import user_sessions
```

And in the router registration section:

```python
app.include_router(user_sessions.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/user_sessions.py backend/app/main.py
git commit -m "feat: add user_sessions API router (SUPER_ADMIN only)"
```

---

## Task 6: Integrate session tracking into auth flow

**Files:**
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/routers/auth.py`
- Modify: `backend/app/dependencies.py`

- [ ] **Step 1: Update `auth_service.login()` to accept IP and user-agent**

In `backend/app/services/auth_service.py`, change the `login()` function signature (line 55) and body to accept and pass through request info:

Change:
```python
async def login(db: AsyncSession, username: str, password: str) -> dict:
```

To:
```python
async def login(
    db: AsyncSession, username: str, password: str,
    ip_address: str | None = None, user_agent: str | None = None,
) -> dict:
```

After `sid = _start_session(user)` (around line 66), add:

```python
    # Close any previous active session for this user
    from app.services import user_session_service
    if user.active_session_id:
        pass  # _start_session already overwrites; old session closed below

    # Start new session (overwrites any existing session — old JWTs become invalid)
    sid = _start_session(user)
    user.last_login = datetime.now(timezone.utc)

    # Track session in user_sessions table
    await user_session_service.start_session(db, user.id, sid, ip_address, user_agent)
```

Wait — the order matters. The old `active_session_id` needs to be closed before `_start_session()` overwrites it. Restructure the login body to:

```python
async def login(
    db: AsyncSession, username: str, password: str,
    ip_address: str | None = None, user_agent: str | None = None,
) -> dict:
    from fastapi import HTTPException, status
    user = await authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Close previous session if one exists
    from app.services import user_session_service
    if user.active_session_id:
        await user_session_service.end_session(db, user.active_session_id, "login_elsewhere")

    # Start new session (overwrites any existing session — old JWTs become invalid)
    sid = _start_session(user)
    user.last_login = datetime.now(timezone.utc)

    # Track session in user_sessions table
    await user_session_service.start_session(db, user.id, sid, ip_address, user_agent)

    extra = {"role": user.role.value, "sid": sid}
    access_token = create_access_token(subject=str(user.id), extra_claims=extra)
    refresh_token = create_refresh_token(subject=str(user.id))

    # Store refresh token in DB
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await token_service.store_refresh_token(db, refresh_token, expires_at, user_id=user.id)

    await db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token}
```

- [ ] **Step 2: Update `auth_service.logout()` to close session**

In `backend/app/services/auth_service.py`, in the `logout()` function (line 119), after `user.session_last_active = None` add:

```python
    if user:
        # Close session tracking record
        if user.active_session_id:
            from app.services import user_session_service
            await user_session_service.end_session(db, user.active_session_id, "logout")
        user.active_session_id = None
        user.session_last_active = None
```

Note: the `end_session` call must come BEFORE clearing `active_session_id`, since it uses that value to find the session row.

- [ ] **Step 3: Update auth router to pass IP and user-agent**

In `backend/app/routers/auth.py`, change the login endpoint (line 44-50) from:

```python
    tokens = await auth_service.login(db, body.username, body.password)
```

To:

```python
    tokens = await auth_service.login(
        db, body.username, body.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
```

- [ ] **Step 4: Update `get_current_user()` heartbeat to also update session table**

In `backend/app/dependencies.py`, change the heartbeat block (lines 78-81) from:

```python
    # Update session activity (throttle to every 30s to reduce DB writes)
    now = datetime.now(timezone.utc)
    if not user.session_last_active or (now - user.session_last_active).total_seconds() > 30:
        user.session_last_active = now
```

To:

```python
    # Update session activity (throttle to every 30s to reduce DB writes)
    now = datetime.now(timezone.utc)
    if not user.session_last_active or (now - user.session_last_active).total_seconds() > 30:
        user.session_last_active = now
        # Also update heartbeat in user_sessions table
        if user.active_session_id:
            from app.services.user_session_service import update_heartbeat
            await update_heartbeat(db, user.active_session_id)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/auth_service.py backend/app/routers/auth.py backend/app/dependencies.py
git commit -m "feat: integrate session tracking into login/logout/heartbeat"
```

---

## Task 7: RBAC menu item

**Files:**
- Modify: `backend/app/core/rbac.py`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Add menu item to SUPER_ADMIN in RBAC**

In `backend/app/core/rbac.py`, add `"User Sessions"` to the SUPER_ADMIN list (after "System Settings", line 30):

```python
        "System Settings",
        "User Sessions",
```

- [ ] **Step 2: Add route mapping in Sidebar**

In `frontend/src/components/Sidebar.tsx`, add to the `MENU_ROUTES` dict (line 25, before the closing `}`):

```typescript
  "Rate Change Logs": "/dashboard/rate-change-logs",
  "Employee Transfer": "/dashboard/transfer",
  "User Sessions": "/dashboard/user-sessions",
```

Note: also add the missing `Rate Change Logs` and `Employee Transfer` routes if they're not already present.

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/rbac.py frontend/src/components/Sidebar.tsx
git commit -m "feat: add User Sessions menu item for SUPER_ADMIN"
```

---

## Task 8: Frontend types

**Files:**
- Create: `frontend/src/types/user-session.ts`

- [ ] **Step 1: Create TypeScript interfaces**

Create `frontend/src/types/user-session.ts`:

```typescript
export interface ActiveSession {
  id: number;
  user_id: string;
  session_id: string;
  started_at: string | null;
  last_heartbeat: string | null;
  ip_address: string | null;
  city: string | null;
  user_agent: string | null;
  full_name: string;
  username: string;
  role: string;
  ticket_count: number | null;
}

export interface SessionHistory extends ActiveSession {
  ended_at: string | null;
  end_reason: string | null;
}

export interface SessionUser {
  id: string;
  full_name: string;
  username: string;
  role: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/user-session.ts
git commit -m "feat: add TypeScript types for user sessions"
```

---

## Task 9: Frontend page

**Files:**
- Create: `frontend/src/app/dashboard/user-sessions/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/dashboard/user-sessions/page.tsx`:

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import DataTable, { Column } from "@/components/dashboard/DataTable";
import type {
  ActiveSession,
  SessionHistory,
  SessionUser,
} from "@/types/user-session";

/* ───── helpers ───── */

function formatDuration(startIso: string | null, endIso?: string | null): string {
  if (!startIso) return "—";
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  const diffMs = end - start;
  if (diffMs < 0) return "—";
  const mins = Math.floor(diffMs / 60_000);
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  if (hrs > 0) return `${hrs}h ${remainMins}m`;
  return `${remainMins}m`;
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function roleBadge(role: string) {
  const colors: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
    SUPER_ADMIN: "destructive",
    ADMIN: "default",
    MANAGER: "secondary",
    BILLING_OPERATOR: "outline",
    TICKET_CHECKER: "outline",
  };
  return (
    <Badge variant={colors[role] || "secondary"}>
      {role.replace(/_/g, " ")}
    </Badge>
  );
}

function endReasonBadge(reason: string | null) {
  if (!reason) return <Badge variant="default">Active</Badge>;
  const map: Record<string, { variant: "default" | "secondary" | "destructive"; label: string }> = {
    logout: { variant: "default", label: "Logout" },
    timeout: { variant: "secondary", label: "Timeout" },
    login_elsewhere: { variant: "destructive", label: "Kicked" },
  };
  const info = map[reason] || { variant: "secondary" as const, label: reason };
  return <Badge variant={info.variant}>{info.label}</Badge>;
}

/* ───── page ───── */

export default function UserSessionsPage() {
  const [tab, setTab] = useState<"live" | "history">("live");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">User Sessions</h1>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2 border-b pb-2">
        <button
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
            tab === "live"
              ? "bg-white border border-b-white -mb-[1px] text-blue-700"
              : "text-gray-500 hover:text-gray-700"
          }`}
          onClick={() => setTab("live")}
        >
          Live Sessions
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
            tab === "history"
              ? "bg-white border border-b-white -mb-[1px] text-blue-700"
              : "text-gray-500 hover:text-gray-700"
          }`}
          onClick={() => setTab("history")}
        >
          Session History
        </button>
      </div>

      {tab === "live" ? <LiveSessions /> : <HistoryTab />}
    </div>
  );
}

/* ───── Live Sessions Tab ───── */

function LiveSessions() {
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.get<ActiveSession[]>("/api/user-sessions/active");
      setSessions(resp.data);
      setError("");
    } catch {
      setError("Failed to load active sessions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const columns: Column<ActiveSession>[] = [
    {
      key: "full_name",
      label: "User",
      render: (s) => (
        <div>
          <span className="font-medium">{s.full_name}</span>
          <span className="text-xs text-gray-400 ml-2">@{s.username}</span>
        </div>
      ),
    },
    {
      key: "role",
      label: "Role",
      render: (s) => roleBadge(s.role),
    },
    {
      key: "ip_address",
      label: "IP / City",
      render: (s) => (
        <div className="text-sm">
          <div>{s.ip_address || "—"}</div>
          {s.city && <div className="text-xs text-gray-400">{s.city}</div>}
        </div>
      ),
    },
    {
      key: "started_at",
      label: "Login Time",
      render: (s) => <span className="text-sm">{formatTime(s.started_at)}</span>,
    },
    {
      key: "duration" as keyof ActiveSession,
      label: "Duration",
      render: (s) => (
        <span className="text-sm font-mono">{formatDuration(s.started_at)}</span>
      ),
    },
    {
      key: "ticket_count",
      label: "Tickets",
      render: (s) =>
        s.ticket_count !== null && s.ticket_count !== undefined ? (
          <span className="font-medium">{s.ticket_count}</span>
        ) : (
          <span className="text-gray-300">—</span>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {sessions.length} active session{sessions.length !== 1 ? "s" : ""}
        </p>
        <Button variant="outline" size="sm" onClick={fetch} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <DataTable
        columns={columns}
        data={sessions}
        totalCount={sessions.length}
        page={1}
        pageSize={sessions.length || 10}
        sortBy=""
        sortOrder="asc"
        onPageChange={() => {}}
        onPageSizeChange={() => {}}
        onSort={() => {}}
        loading={loading}
        emptyMessage="No active sessions."
      />
    </div>
  );
}

/* ───── History Tab ───── */

function HistoryTab() {
  const [sessions, setSessions] = useState<SessionHistory[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [users, setUsers] = useState<SessionUser[]>([]);

  // Load user list for filter dropdown
  useEffect(() => {
    api
      .get<SessionUser[]>("/api/user-sessions/users")
      .then((r) => setUsers(r.data))
      .catch(() => {});
  }, []);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * pageSize),
        limit: String(pageSize),
      });
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      if (userFilter) params.set("user_id", userFilter);

      const countParams = new URLSearchParams();
      if (dateFrom) countParams.set("date_from", dateFrom);
      if (dateTo) countParams.set("date_to", dateTo);
      if (userFilter) countParams.set("user_id", userFilter);

      const [dataResp, countResp] = await Promise.all([
        api.get<SessionHistory[]>(`/api/user-sessions/history?${params}`),
        api.get<number>(`/api/user-sessions/history/count?${countParams}`),
      ]);
      setSessions(dataResp.data);
      setTotalCount(countResp.data as unknown as number);
      setError("");
    } catch {
      setError("Failed to load session history.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, dateFrom, dateTo, userFilter]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const columns: Column<SessionHistory>[] = [
    {
      key: "full_name",
      label: "User",
      render: (s) => (
        <div>
          <span className="font-medium">{s.full_name}</span>
          <span className="text-xs text-gray-400 ml-2">@{s.username}</span>
        </div>
      ),
    },
    {
      key: "role",
      label: "Role",
      render: (s) => roleBadge(s.role),
    },
    {
      key: "started_at",
      label: "Login",
      render: (s) => <span className="text-sm">{formatTime(s.started_at)}</span>,
    },
    {
      key: "ended_at",
      label: "Logout",
      render: (s) => <span className="text-sm">{formatTime(s.ended_at)}</span>,
    },
    {
      key: "duration" as keyof SessionHistory,
      label: "Duration",
      render: (s) => (
        <span className="text-sm font-mono">
          {formatDuration(s.started_at, s.ended_at)}
        </span>
      ),
    },
    {
      key: "end_reason",
      label: "End Reason",
      render: (s) => endReasonBadge(s.end_reason),
    },
    {
      key: "ip_address",
      label: "IP / City",
      render: (s) => (
        <div className="text-sm">
          <div>{s.ip_address || "—"}</div>
          {s.city && <div className="text-xs text-gray-400">{s.city}</div>}
        </div>
      ),
    },
    {
      key: "ticket_count",
      label: "Tickets",
      render: (s) =>
        s.ticket_count !== null && s.ticket_count !== undefined ? (
          <span className="font-medium">{s.ticket_count}</span>
        ) : (
          <span className="text-gray-300">—</span>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
            className="border rounded-md px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
            className="border rounded-md px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">User</label>
          <select
            value={userFilter}
            onChange={(e) => {
              setUserFilter(e.target.value);
              setPage(1);
            }}
            className="border rounded-md px-3 py-1.5 text-sm min-w-[180px]"
          >
            <option value="">All Users</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name} ({u.role.replace(/_/g, " ")})
              </option>
            ))}
          </select>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setDateFrom("");
            setDateTo("");
            setUserFilter("");
            setPage(1);
          }}
        >
          Clear Filters
        </Button>
        <Button variant="outline" size="sm" onClick={fetchHistory} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <DataTable
        columns={columns}
        data={sessions}
        totalCount={totalCount}
        page={page}
        pageSize={pageSize}
        sortBy=""
        sortOrder="asc"
        onPageChange={setPage}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPage(1);
        }}
        onSort={() => {}}
        loading={loading}
        emptyMessage="No session history found."
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/dashboard/user-sessions/page.tsx
git commit -m "feat: add User Sessions dashboard page with live + history tabs"
```

---

## Task 10: End-to-end verification

- [ ] **Step 1: Run Alembic migration**

```bash
cd backend
python -m alembic upgrade head
```

- [ ] **Step 2: Start backend and verify API**

```bash
cd backend
uvicorn app.main:app --reload
```

Test login creates a session:
```bash
curl -s -c cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"Password@123"}'
```

Extract token from cookies and test active sessions:
```bash
TOKEN=$(grep ssmspl_access_token cookies.txt | awk '{print $NF}')
curl -s http://localhost:8000/api/user-sessions/active \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Expected: JSON array with one session entry for superadmin.

- [ ] **Step 3: Start frontend and verify page**

```bash
cd frontend
npm run dev
```

1. Login as superadmin at `http://localhost:3000/login`
2. Navigate to `/dashboard/user-sessions`
3. Verify Live Sessions tab shows the current session
4. Verify Session History tab shows the session
5. Verify Refresh button works

- [ ] **Step 4: Test logout creates session end**

1. Click logout
2. Login again as superadmin
3. Navigate to User Sessions > Session History tab
4. Verify previous session shows `end_reason: "logout"`

- [ ] **Step 5: Final commit with deployment log**

Update `updates_to_deploy_logs.md` with the new feature entry, then:

```bash
git add -A
git commit -m "feat: user session monitoring — live + history dashboard for SUPER_ADMIN"
```
