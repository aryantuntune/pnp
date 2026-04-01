# Dashboard Enhancements & Remaining Issues

This document summarizes the recent overhaul of the dashboard analytics functionality. We have completely transitioned the dashboard from a static, mount-only view to a fully dynamic, date-aware reporting hub.

## ✅ Completed Enhancements

### 1. Data Freshness & Date Selection
- **Historical Data Access:** Admins and managers can now view historical analytics using new "Today", "Yesterday", and Calendar picker actions.
- **Auto-Refresh Mechanism:** Implemented a 5-minute auto-refresh interval. This safely pauses when examining historical dates, preventing the UI from abruptly reverting to "Today."
- **Status Badges:** Added dynamic "Live" (with pulsing animation) and "Historical" status badges.
- **Timestamp Indicator:** Added an "Updated X min ago" label that ticks automatically every 30 seconds to show data freshness.

### 2. Revamped Charts & Visualizations
- **Dual-Axis Revenue Chart:** The main Revenue Trend chart is now a `ComposedChart`. It plots absolute revenue (blue bars) on the left axis and ticket volume (amber line) on the right axis.
- **Item Volume Chart:** Created a brand-new `ItemQuantityChart` component. This plots ticket quantities in a horizontal bar format, color-coding vehicles (blue) vs. passengers (green).
- **Date Range Toggles:** Added `7D`, `30D`, and `MTD` (Month-to-Date) fast-filter options to the Revenue Trend chart.

### 3. Summary & Tables
- **ATV Metric:** Inserted a new "Average Ticket Value" (ATV) summary card into the main overview grid.
- **Cancellation Tracking:** Added a red chip specifically tracking cancelled tickets across the overall collection.
- **Inline Progress Bars:** Replaced static table numbers with smooth, inline background progress bars for both the **Branch Breakdown** and **Payment Mode** tables to help quickly spot top performers.
- **Enhanced Empty States:** Replaced generic "No data" strings with proper icon-based UI states that dynamically re-word themselves based on whether you are querying today or a historical date.

### 4. Backend Support Adjustments
- Updated `/stats` and `/today-summary` FastAPI endpoints to accept an optional `?date=` query parameter.
- Augmented the `dashboard_service` to return `cancelled_count` per branch.
- Upgraded the `report_service` to return `ticket_count` inside revenue grouped aggregations.

---

## Resolved Loose Ends (2026-04-02)

All functional issues have been patched.

- **Branch Cancellations (Fixed):** `cancelled_count` is now mapped in the frontend `TodaySummary` TypeScript interface and displayed as a red "Cancelled" column in the Branch Breakdown table.
- **WebSocket Race Condition (Fixed):** Added a `wsHasData` ref that tracks whether WebSocket has already delivered live stats. The HTTP stats callback skips `setStats()` when WS data is already present, preventing stale HTTP payloads from overwriting fresh WS state.
- **Backend Aggregation (Optimized):** `total_tickets`, `total_cancelled`, and `total_revenue` are now computed via a single Postgres-level `SELECT` with `func.count()` / `func.sum()` instead of Python `sum()` list comprehensions.

> [!NOTE]
> **Lingering IDE Linting Error (Non-functional)**
>
> The backend `schemas/dashboard.py` file triggers a Pyre2 error: `Could not find import of pydantic`. This is purely an environment/IDE resolution quirk and does not impact FastAPI's Pydantic runtime.
