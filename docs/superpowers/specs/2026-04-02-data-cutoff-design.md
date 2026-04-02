# Data Cutoff: Hide Pre-April 2026 Ticket Data for Non-SUPER_ADMIN

**Date:** 2026-04-02
**Status:** Draft

## Problem

The system went live in March 2026 but real production data only started April 1, 2026. The client wants all March (and earlier) ticket data hidden from non-SUPER_ADMIN users. Data must not be deleted — just invisible to ADMIN, MANAGER, BILLING_OPERATOR, and TICKET_CHECKER roles.

## Design Decisions

- **Cutoff date:** Hardcoded `2026-04-01` (not configurable)
- **Scope:** Only ticket data (`tickets` table) — no bookings or other data existed before April
- **SUPER_ADMIN:** Always sees all data, no restrictions, no toggle needed
- **Enforcement:** Frontend blocks date selection + backend clamps dates as safety net
- **Trigger:** Only activates when a user explicitly requests a date before the cutoff (not on every query)

## Architecture

### Backend: Centralized Date Clamping Utility

**New file: `backend/app/core/data_cutoff.py`**

```python
import datetime
from app.core.rbac import UserRole

DATA_CUTOFF_DATE = datetime.date(2026, 4, 1)

def clamp_date_from(d: datetime.date | None, user_role: str) -> datetime.date | None:
    """Clamp date_from to DATA_CUTOFF_DATE for non-SUPER_ADMIN users."""
    if user_role == UserRole.SUPER_ADMIN:
        return d
    if d is not None and d < DATA_CUTOFF_DATE:
        return DATA_CUTOFF_DATE
    return d

def clamp_date_to(d: datetime.date | None, user_role: str) -> datetime.date | None:
    """Clamp date_to — if it's before cutoff, return day-before-cutoff to yield empty results."""
    if user_role == UserRole.SUPER_ADMIN:
        return d
    if d is not None and d < DATA_CUTOFF_DATE:
        return DATA_CUTOFF_DATE - datetime.timedelta(days=1)
    return d

def clamp_single_date(d: datetime.date | None, user_role: str) -> datetime.date | None:
    """For single-date reports: clamp to cutoff date if before it."""
    if user_role == UserRole.SUPER_ADMIN:
        return d
    if d is not None and d < DATA_CUTOFF_DATE:
        return DATA_CUTOFF_DATE
    return d
```

**Logic:**
- `clamp_date_from`: If `date_from < 2026-04-01`, move it up to `2026-04-01`. A range like `Mar 15 – Apr 10` becomes `Apr 01 – Apr 10`.
- `clamp_date_to`: If `date_to < 2026-04-01`, set it to `Mar 31` — combined with a clamped `date_from` of `Apr 01`, the query returns empty results naturally.
- `clamp_single_date`: For single-date endpoints, clamp to `Apr 01` so a request for any March date returns April 1 data instead. (These endpoints would show April 1 data rather than March data.)
- All functions pass through `None` unchanged (no clamping when no date is provided, since defaults are always "today").

### Backend: Router-Level Application

Clamping is applied at the **router level**, right after receiving query params and before passing to services. This keeps services unchanged and puts the enforcement where dates enter the system.

#### Files Modified

**1. `backend/app/routers/tickets.py`**

In `list_tickets()` and `count_tickets()` — after the existing BILLING_OPERATOR date override, add clamping for all other roles:

```python
from app.core.data_cutoff import clamp_date_from, clamp_date_to

# In list_tickets(), after BILLING_OPERATOR block:
date_from = clamp_date_from(date_from, current_user.role)
date_to = clamp_date_to(date_to, current_user.role)

# Same in count_tickets()
```

**2. `backend/app/routers/reports.py`**

All 12 report endpoints + their PDF variants need clamping. Two patterns:

For **date-range endpoints** (revenue, ticket-count, item-breakdown, branch-summary, payment-mode, date-wise-amount, itemwise-levy, branch-item-summary):
```python
date_from = clamp_date_from(date_from, current_user.role)
date_to = clamp_date_to(date_to, current_user.role)
```

For **single-date endpoints** (ferry-wise-item, user-wise-summary, vehicle-wise-tickets, ticket-details):
```python
date = clamp_single_date(date, current_user.role)
```

**3. `backend/app/routers/dashboard.py`**

In `stats()` and `today_summary()`:
```python
from app.core.data_cutoff import clamp_single_date

for_date = clamp_single_date(for_date, current_user.role)
```

Note: Dashboard defaults to today when `for_date` is None, so clamping only activates if someone explicitly passes an old date.

**4. `backend/app/routers/rate_change_logs.py`**

In `get_rate_change_logs()` and `count_rate_change_logs()`:
```python
date_from = clamp_date_from(date_from, current_user.role)
date_to = clamp_date_to(date_to, current_user.role)
```

### Frontend: Block Date Selection Before Cutoff

Add `min` attribute to all date inputs for non-SUPER_ADMIN users. The cutoff constant is defined once.

**New constant in `frontend/src/lib/constants.ts` (or inline):**
```typescript
export const DATA_CUTOFF_DATE = "2026-04-01";
```

#### Files Modified

**1. `frontend/src/app/dashboard/page.tsx` (line ~555)**
- Add `min={user?.role !== "SUPER_ADMIN" ? DATA_CUTOFF_DATE : undefined}` to the date input

**2. `frontend/src/app/dashboard/reports/page.tsx` (lines ~739-767)**
- Add `min` to all 3 date inputs (dateFrom, dateTo, singleDate)
- User object is already fetched via `/api/auth/me`; store it in state if not already

**3. `frontend/src/app/dashboard/rate-change-logs/page.tsx` (lines ~182-202)**
- Add `min` to both dateFrom and dateTo inputs
- Need to add user fetch (currently not present) to check role

**4. `frontend/src/app/dashboard/ticketing/page.tsx` (lines ~1371-1395, ~1816-1828)**
- Add `min` to dateFrom, dateTo filter inputs and formTicketDate input
- User object already available via `user?.role`

**5. `frontend/src/app/dashboard/multiticketing/page.tsx`**
- No date inputs exposed to user — no changes needed

### Files Changed Summary

| File | Change |
|------|--------|
| `backend/app/core/data_cutoff.py` | **NEW** — cutoff constant + 3 clamp functions |
| `backend/app/routers/tickets.py` | Add 4 lines (2 per function) |
| `backend/app/routers/reports.py` | Add 2 lines per endpoint (~28 lines total across 12+6 endpoints) |
| `backend/app/routers/dashboard.py` | Add 2 lines (1 per function) |
| `backend/app/routers/rate_change_logs.py` | Add 4 lines (2 per function) |
| `frontend/src/lib/constants.ts` | **NEW** or add 1 line |
| `frontend/src/app/dashboard/page.tsx` | Add `min` to 1 date input |
| `frontend/src/app/dashboard/reports/page.tsx` | Add `min` to 3 date inputs + user state |
| `frontend/src/app/dashboard/rate-change-logs/page.tsx` | Add `min` to 2 date inputs + user fetch |
| `frontend/src/app/dashboard/ticketing/page.tsx` | Add `min` to 3 date inputs |

## Edge Cases

1. **No date provided (None/null):** Pass through unchanged. Defaults are always "today" which is after cutoff.
2. **Entire range before cutoff (e.g., Mar 1–Mar 31):** `date_from` clamped to Apr 1, `date_to` stays at Mar 31 → `from > to` → empty results.
3. **Range spanning cutoff (e.g., Mar 15–Apr 10):** `date_from` clamped to Apr 1 → shows Apr 1–10 only.
4. **Single date before cutoff (e.g., Mar 25):** Clamped to Apr 1 → shows Apr 1 data.
5. **BILLING_OPERATOR:** Already forced to today in tickets router. Cutoff clamping runs after, which is a no-op since today > cutoff.
6. **Direct API calls (bypassing frontend):** Backend clamping catches these.
7. **Dashboard defaults:** `for_date=None` → service defaults to today → no clamping needed.

## Testing

Manual verification:
- As ADMIN: try selecting March dates in reports → frontend blocks it, backend clamps if bypassed
- As SUPER_ADMIN: select March dates → see old ticket data
- As MANAGER: default dashboard view → unchanged, shows today's data
- Verify reports with date ranges spanning March–April only show April portion for non-SUPER_ADMIN
