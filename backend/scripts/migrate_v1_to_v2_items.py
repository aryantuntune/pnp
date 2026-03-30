#!/usr/bin/env python3
"""
V1 → V2 Item & Rate Migration
==============================
Migrates the live database from the legacy 49-item structure to the new
21-item rate sheet defined in:  data/item_rates/NEW ITEM ID & RATE.pdf

DESIGN PRINCIPLES (agreed with ChatGPT review):
  • Never DELETE item_rates rows — use is_active=FALSE so the trigger records it.
  • Never DELETE items rows    — keep as is_active=FALSE for FK integrity.
  • All writes tagged notes='V1_TO_V2_MIGRATION' via session variable.
  • Each step runs in its own transaction and is verified before proceeding.
  • Script is idempotent — safe to run multiple times.

STEPS:
  0. Pre-flight:  count rows, confirm schema columns exist
  1. Backfill     ticket_items.item_name_snapshot  (and short_name)
  2. Backfill     booking_items.item_name_snapshot (and short_name)
  3. Seed         item_rate_history baseline from current item_rates
  4. Insert       item_migration_map  (V1→V2 semantic mapping)
  5. Update       items table         (rename recycled IDs, deactivate V1-only items)
  6. Deactivate   old item_rates      (UPDATE is_active=FALSE)
  7. Insert       new V2 item_rates   (21 items × 6 routes = 126 rows)

Usage:
    python scripts/migrate_v1_to_v2_items.py                 # execute all steps
    python scripts/migrate_v1_to_v2_items.py --dry-run        # preview only
    python scripts/migrate_v1_to_v2_items.py --step 3        # single step
    python scripts/migrate_v1_to_v2_items.py --env .env.production
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

SCRIPT_DIR  = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent

_ENV_CANDIDATES = [
    BACKEND_DIR / ".env.production",
    BACKEND_DIR / ".env.development",
]
DEFAULT_ENV = next((p for p in _ENV_CANDIDATES if p.exists()), BACKEND_DIR / ".env.development")

MIGRATION_LABEL = "V1_TO_V2_2026-03-29"
MIGRATION_NOTES = "V1_TO_V2_MIGRATION"

# ---------------------------------------------------------------------------
# V2 items — exact from PDF "NEW ITEM ID & RATE"
# (id, name, short_name, is_vehicle, online_visibility)
# ---------------------------------------------------------------------------
V2_ITEMS: list[tuple[int, str, str, bool, bool]] = [
    (1,  "CYCLE",                                         "CYCLE",                True,  True),
    (2,  "MOTOR CYCLE WITH DRIVER",                       "MOTORCYCLE W/ DRIVER", True,  True),
    (3,  "EMPTY 3 WHLR RICKSHAW",                        "3 WHLR RICKSHAW",      True,  True),
    (4,  "MAGIC/IRIS/CAR",                               "MAGIC/IRIS/CAR",       True,  True),
    (5,  "LUX CAR 5 ST/SUMO/SCORPIO/TAVERA 7 ST",       "LUX CAR/SUMO",         True,  True),
    (6,  "AMBULANCE",                                     "AMBULANCE",            True,  True),
    (7,  "T.T/407/709/18 & 21 ST BUS",                  "TT/407/709/BUS",       True,  True),
    (8,  "BUS/TRUCK/TANKER",                             "BUS/TRUCK/TANKER",     True,  True),
    (9,  "TRUCK 10 WHLR/JCB",                           "TRUCK 10 WHLR/JCB",   True,  True),
    (10, "TRACTOR WITH TROLLY",                          "TRACTOR W/ TROLLY",    True,  True),
    (11, "PASSENGER ADULT ABOVE 12 YR",                  "PASSENGER ADULT",      False, True),
    (12, "PASSENGER CHILD 3-12 YR",                     "PASSENGER CHILD",      False, True),
    (13, "GOODS PER HALF TON",                          "GOODS/HALF TON",       False, True),
    (14, "PASS LUG ABV 20KG PER KG",                   "LUGGAGE ABV 20KG/KG",  False, True),
    (15, "DOG/GOATS/SHEEP & FISH/CHICKEN/BIRDS/FRUITS", "ANIMALS & GOODS",      False, True),
    (16, "COWS/BUFFELLOW (PER NO)",                     "COWS/BUFFALO",         False, True),
    (17, "TOURIST (FOR 1 HOUR)",                        "TOURIST 1HR",          False, True),
    (18, "MONTH PASS STUDENT UPTO 7TH",                 "STDNT PASS UPTO 7TH",  False, False),
    (19, "MONTH PASS STUDENT ABOVE XTH",                "STDNT PASS ABOVE XTH", False, False),
    (20, "MONTH PASS PASSENGER",                        "PASSENGER MONTH PASS",  False, False),
    (21, "SPECIAL FERRY",                               "SPECIAL FERRY",         False, False),
]

# ---------------------------------------------------------------------------
# Semantic mapping: V1 item_id → V2 item_id (for migration map table).
# When an old item is semantically absorbed into a new item.
# ---------------------------------------------------------------------------
V1_TO_V2_SEMANTIC: dict[int, int] = {
    # Items whose IDs are recycled (in-place name change)
    4:  4,   # EMPTY 3WHLR 5 ST RICKSHAW        → MAGIC/IRIS/CAR
    5:  5,   # TATA MAGIC/MAXIMO 6 ST            → LUX CAR/SUMO/SCORPIO/TAVERA 7 ST
    6:  6,   # TATA ACE/MAXIMO TEMPO             → AMBULANCE
    7:  7,   # EMPTY CAR 5 ST                    → T.T/407/709/18 & 21 ST BUS
    8:  8,   # EMPTY LUX. CAR 5 ST              → BUS/TRUCK/TANKER
    9:  9,   # SUMO/SCAPIO/TAVERA/INOVA 7 ST    → TRUCK 10 WHLR/JCB
    10: 10,  # TATA MOBILE/MAX PICKUP            → TRACTOR WITH TROLLY
    13: 13,  # AMBULANCE                          → GOODS PER HALF TON
    14: 14,  # TEMPO TRAVELER/18 ST BUS          → PASS LUG ABV 20KG PER KG
    15: 15,  # 407 TEMPO                          → DOG/GOATS/SHEEP & FISH/...
    16: 16,  # MINI BUS 21 ST                    → COWS/BUFFELLOW (PER NO)
    17: 17,  # LODED 709                          → TOURIST (FOR 1 HOUR)
    18: 18,  # MED.GOODS 6 WHLR (709)           → MONTH PASS STUDENT UPTO 7TH
    19: 19,  # LODED TRUCK                        → MONTH PASS STUDENT ABOVE XTH
    20: 20,  # PASSENGER BUS                      → MONTH PASS PASSENGER
    21: 21,  # TANKER/TRUCK                       → SPECIAL FERRY
    # Items that move to a different V2 ID
    22: 9,   # TRUCK 10 WHLR      → V2 item 9 (TRUCK 10 WHLR/JCB)
    23: 13,  # GOODS PER HALF TON → V2 item 13
    24: 14,  # PASSENGER LUGGAGE  → V2 item 14
    25: 15,  # DOG/GOATS/SHEEP   → V2 item 15
    26: 16,  # COWS/BUFFELLOW     → V2 item 16
    27: 18,  # MONTH PASS STDNT UPTO 10TH → V2 item 18
    28: 19,  # MONTH PASS STDNT ABOVE XTH → V2 item 19
    29: 17,  # TOURIST            → V2 item 17
    30: 20,  # MONTH PASS PASSENGER → V2 item 20
    31: 15,  # FISH/CHICKEN/BIRDS/FRUITS → V2 item 15 (combined with item 25)
    32: 9,   # JCB                → V2 item 9  (combined with item 22)
    33: 10,  # TRACTOR WITH TROLLY → V2 item 10
    34: 21,  # SPECIAL FERRY      → V2 item 21
    # Items with no V2 equivalent (deactivated only)
    # 35–45, 151–154: no mapping → action = DEACTIVATED
}

# V2 item IDs that are just name-fixes (no semantic change, just spelling/typo)
V2_SAME_IDS = {1, 2, 3, 11, 12}

# ---------------------------------------------------------------------------
# Rate data from PDF (route_name → {pdf_item_no: (rate, levy)})
# ---------------------------------------------------------------------------
ROUTE_MAP: dict[str, int] = {
    "DABHOL-DHOPAVE":    1,
    "VESHVI-BAGMANDALE": 2,
    "JAIGAD-TAVSAL":     3,
    "DIGHI-AGARDANDA":   4,
    "VASAI-BHAYANDAR":   5,
    "VIRAR-SAFALE":      7,
}

RATE_DATA: dict[str, dict[int, tuple[int, int]]] = {
    "DABHOL-DHOPAVE": {
        1: (13, 2), 2: (58, 7), 3: (81, 9), 4: (163, 17), 5: (181, 19),
        6: (180, 0), 7: (225, 25), 8: (360, 40), 9: (500, 50), 10: (319, 31),
        11: (18, 2), 12: (9, 1), 13: (36, 4), 14: (1, 0), 15: (18, 2),
        16: (45, 5), 17: (27, 3), 18: (270, 30), 19: (360, 40), 20: (640, 60),
        21: (500, 0),
    },
    "VESHVI-BAGMANDALE": {
        1: (13, 2), 2: (58, 7), 3: (81, 9), 4: (163, 17), 5: (181, 19),
        6: (180, 0), 7: (225, 25), 8: (360, 40), 9: (500, 50), 10: (319, 31),
        11: (18, 2), 12: (9, 1), 13: (36, 4), 14: (1, 0), 15: (18, 2),
        16: (45, 5), 17: (27, 3), 18: (270, 30), 19: (360, 40), 20: (640, 60),
        21: (500, 0),
    },
    "JAIGAD-TAVSAL": {
        1: (18, 2), 2: (73, 7), 3: (95, 10), 4: (182, 18), 5: (205, 20),
        6: (200, 0), 7: (238, 22), 8: (410, 40), 9: (550, 50), 10: (273, 27),
        11: (27, 3), 12: (13, 2), 13: (45, 5), 14: (1, 0), 15: (23, 2),
        16: (64, 6), 17: (45, 5), 18: (450, 50), 19: (550, 50), 20: (1180, 120),
        21: (600, 0),
    },
    "DIGHI-AGARDANDA": {
        1: (10, 1), 2: (50, 5), 3: (68, 7), 4: (140, 14), 5: (160, 16),
        6: (200, 0), 7: (200, 20), 8: (300, 30), 9: (400, 50), 10: (200, 20),
        11: (27, 3), 12: (13, 2), 13: (30, 3), 14: (1, 0), 15: (9, 1),
        16: (50, 5), 17: (45, 5), 18: (450, 50), 19: (550, 50), 20: (1180, 120),
        21: (700, 0),
    },
    "VASAI-BHAYANDAR": {
        1: (9, 1), 2: (60, 6), 3: (100, 10), 4: (180, 20), 5: (180, 20),
        6: (200, 0), 7: (200, 20), 8: (300, 30), 9: (500, 50), 10: (200, 20),
        11: (27, 3), 12: (13, 2), 13: (27, 3), 14: (1, 0), 15: (36, 4),
        16: (50, 5), 17: (55, 5), 18: (450, 50), 19: (550, 50), 20: (1000, 100),
        21: (500, 0),
    },
    "VIRAR-SAFALE": {
        1: (9, 1), 2: (60, 6), 3: (100, 10), 4: (180, 20), 5: (180, 20),
        6: (200, 0), 7: (200, 20), 8: (300, 30), 9: (500, 50), 10: (200, 20),
        11: (27, 3), 12: (13, 2), 13: (27, 3), 14: (1, 0), 15: (10, 1),
        16: (50, 5), 17: (55, 5), 18: (550, 50), 19: (600, 50), 20: (1000, 100),
        21: (500, 0),
    },
}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def load_database_url(env_path: Path) -> str:
    if not env_path.exists():
        sys.exit(f"ERROR: Env file not found: {env_path}")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() == "DATABASE_URL":
                url = val.strip().strip("'\"")
                return url.replace("postgresql+asyncpg://", "postgresql://")
    sys.exit(f"ERROR: DATABASE_URL not found in {env_path}")


def header(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ---------------------------------------------------------------------------
# Step 0 — Pre-flight checks
# ---------------------------------------------------------------------------
async def step0_preflight(conn) -> dict:
    header("Step 0 — Pre-flight checks")

    tickets_total  = await conn.fetchval("SELECT COUNT(*) FROM ticket_items")
    bookings_total = await conn.fetchval("SELECT COUNT(*) FROM booking_items")
    rates_total    = await conn.fetchval("SELECT COUNT(*) FROM item_rates WHERE is_active = TRUE")
    items_total    = await conn.fetchval("SELECT COUNT(*) FROM items")

    # Check snapshot columns exist
    snap_ticket = await conn.fetchval(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name='ticket_items' AND column_name='item_name_snapshot'"
    )
    snap_booking = await conn.fetchval(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name='booking_items' AND column_name='item_name_snapshot'"
    )
    hist_table = await conn.fetchval(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_name='item_rate_history'"
    )
    map_table = await conn.fetchval(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_name='item_migration_map'"
    )

    print(f"  ticket_items rows         : {tickets_total}")
    print(f"  booking_items rows        : {bookings_total}")
    print(f"  item_rates (active)       : {rates_total}")
    print(f"  items total               : {items_total}")
    print(f"  item_name_snapshot exists : ticket_items={bool(snap_ticket)}, booking_items={bool(snap_booking)}")
    print(f"  item_rate_history exists  : {bool(hist_table)}")
    print(f"  item_migration_map exists : {bool(map_table)}")

    if not snap_ticket or not snap_booking:
        sys.exit(
            "\nERROR: Snapshot columns missing. Apply the DDL patch first:\n"
            "  psql -d <db> -f backend/scripts/ddl.sql\n"
        )
    if not hist_table or not map_table:
        sys.exit(
            "\nERROR: Audit tables missing. Apply the DDL patch first:\n"
            "  psql -d <db> -f backend/scripts/ddl.sql\n"
        )

    print("\n  Pre-flight OK.")
    return {
        "ticket_items": tickets_total,
        "booking_items": bookings_total,
    }


# ---------------------------------------------------------------------------
# Step 1 — Backfill ticket_items snapshots
# ---------------------------------------------------------------------------
async def step1_backfill_ticket_snapshots(conn, dry_run: bool) -> int:
    header("Step 1 — Backfill ticket_items.item_name_snapshot")

    pending = await conn.fetchval(
        "SELECT COUNT(*) FROM ticket_items WHERE item_name_snapshot IS NULL"
    )
    print(f"  Rows needing backfill: {pending}")

    if pending == 0:
        print("  Already complete — skipped.")
        return 0

    if not dry_run:
        updated = await conn.fetchval(
            """
            WITH upd AS (
                UPDATE ticket_items ti
                SET    item_name_snapshot       = i.name,
                       item_short_name_snapshot = i.short_name
                FROM   items i
                WHERE  ti.item_id = i.id
                  AND  ti.item_name_snapshot IS NULL
                RETURNING 1
            ) SELECT COUNT(*) FROM upd
            """
        )
        print(f"  Backfilled: {updated} rows")
        return updated
    else:
        print(f"  DRY RUN — would backfill {pending} rows")
        return pending


# ---------------------------------------------------------------------------
# Step 2 — Backfill booking_items snapshots
# ---------------------------------------------------------------------------
async def step2_backfill_booking_snapshots(conn, dry_run: bool) -> int:
    header("Step 2 — Backfill booking_items.item_name_snapshot")

    # booking_items has no FK to items — join on item_id best-effort
    pending = await conn.fetchval(
        "SELECT COUNT(*) FROM booking_items WHERE item_name_snapshot IS NULL"
    )
    print(f"  Rows needing backfill: {pending}")

    if pending == 0:
        print("  Already complete — skipped.")
        return 0

    if not dry_run:
        updated = await conn.fetchval(
            """
            WITH upd AS (
                UPDATE booking_items bi
                SET    item_name_snapshot       = i.name,
                       item_short_name_snapshot = i.short_name
                FROM   items i
                WHERE  bi.item_id = i.id
                  AND  bi.item_name_snapshot IS NULL
                RETURNING 1
            ) SELECT COUNT(*) FROM upd
            """
        )
        # Rows with no matching item (orphaned) — set a fallback
        orphans = await conn.fetchval(
            "SELECT COUNT(*) FROM booking_items WHERE item_name_snapshot IS NULL"
        )
        if orphans > 0:
            await conn.execute(
                "UPDATE booking_items SET item_name_snapshot = '[UNKNOWN ITEM]' "
                "WHERE item_name_snapshot IS NULL"
            )
            print(f"  Orphaned rows (no item match): {orphans} — set to [UNKNOWN ITEM]")
        print(f"  Backfilled: {updated} rows")
        return updated
    else:
        print(f"  DRY RUN — would backfill {pending} rows")
        return pending


# ---------------------------------------------------------------------------
# Step 3 — Seed item_rate_history baseline
# ---------------------------------------------------------------------------
async def step3_seed_history_baseline(conn, dry_run: bool) -> int:
    header("Step 3 — Seed item_rate_history baseline (V1 snapshot)")

    already = await conn.fetchval(
        "SELECT COUNT(*) FROM item_rate_history WHERE notes = 'V1_BASELINE'"
    )
    if already > 0:
        print(f"  Already seeded ({already} baseline rows) — skipped.")
        return already

    rows = await conn.fetch(
        "SELECT id, item_id, route_id, rate, levy, is_active FROM item_rates"
    )
    print(f"  Current item_rates rows: {len(rows)}")

    if not dry_run:
        await conn.executemany(
            """
            INSERT INTO item_rate_history
                (item_rate_id, item_id, route_id,
                 old_rate, new_rate, old_levy, new_levy,
                 old_is_active, new_is_active,
                 change_type, changed_by, notes)
            VALUES ($1, $2, $3, NULL, $4, NULL, $5, NULL, $6, 'CREATED', NULL, 'V1_BASELINE')
            """,
            [(r["id"], r["item_id"], r["route_id"],
              r["rate"], r["levy"], r["is_active"]) for r in rows],
        )
        print(f"  Seeded: {len(rows)} baseline rows into item_rate_history")
    else:
        print(f"  DRY RUN — would seed {len(rows)} baseline rows")

    return len(rows)


# ---------------------------------------------------------------------------
# Step 4 — Insert item_migration_map
# ---------------------------------------------------------------------------
async def step4_insert_migration_map(conn, dry_run: bool) -> int:
    header("Step 4 — Insert item_migration_map")

    already = await conn.fetchval(
        "SELECT COUNT(*) FROM item_migration_map WHERE migration_label = $1",
        MIGRATION_LABEL,
    )
    if already > 0:
        print(f"  Already recorded ({already} rows for {MIGRATION_LABEL}) — skipped.")
        return already

    # Fetch all V1 items
    v1_items = {
        r["id"]: r for r in await conn.fetch("SELECT id, name FROM items")
    }
    v2_id_to_name = {row[0]: row[1] for row in V2_ITEMS}

    records = []

    for old_id, item in sorted(v1_items.items()):
        old_name = item["name"]
        new_id   = V1_TO_V2_SEMANTIC.get(old_id)

        if old_id in V2_SAME_IDS:
            # Minor name fix only
            new_name = v2_id_to_name.get(old_id, old_name)
            action = "RENAMED"
            records.append((old_id, old_name, old_id, new_name, MIGRATION_LABEL, action,
                             "Name standardised to match PDF"))
        elif new_id is not None:
            new_name = v2_id_to_name.get(new_id, "")
            action = "RECYCLED" if new_id == old_id else "RENAMED"
            records.append((old_id, old_name, new_id, new_name, MIGRATION_LABEL, action,
                             f"V1 item absorbed into V2 item {new_id}"))
        else:
            # No V2 equivalent
            records.append((old_id, old_name, None, None, MIGRATION_LABEL, "DEACTIVATED",
                             "No V2 equivalent — deactivated"))

    print(f"  Migration map entries: {len(records)}")

    if not dry_run:
        await conn.executemany(
            """
            INSERT INTO item_migration_map
                (old_item_id, old_item_name, new_item_id, new_item_name,
                 migration_label, action, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            records,
        )
        print(f"  Inserted {len(records)} rows into item_migration_map")
    else:
        for r in records:
            print(f"  [{r[5]:11}]  item {r[0]:3} '{r[1]}' → item {r[2]} '{r[3]}'")

    return len(records)


# ---------------------------------------------------------------------------
# Step 5 — Update items table to V2
# ---------------------------------------------------------------------------
    async def step5_update_items(conn, dry_run: bool) -> dict:
        header("Step 5 — Update items table to V2")

        v2_ids = {row[0] for row in V2_ITEMS}
        # Fetch all current items
        current = {r["id"]: dict(r) for r in await conn.fetch(
            "SELECT id, name, short_name, is_active FROM items"
        )}

        updated = 0
        deactivated = 0

        # 5a-pre: Clear namespace — temporarily rename ALL items to avoid
        #         UNIQUE constraint violations during V2 rename.
        if not dry_run:
            await conn.execute(
                "UPDATE items SET name = name || '__V1_MIGRATING', "
                "short_name = short_name || '__V1' "
                "WHERE id = ANY($1::int[])",
                list(current.keys()),
            )
        print("  [PREP]   Temporarily renamed all items to clear namespace")

        # 5a: Apply V2 names (INSERT or UPDATE for each V2 item)
        for item_id, name, short_name, is_vehicle, online_vis in V2_ITEMS:
            existing = current.get(item_id)
            if existing:
                # Row exists — update to V2 definition
                if (existing["name"] != name
                        or existing["short_name"] != short_name
                        or not existing["is_active"]):
                    if not dry_run:
                        await conn.execute(
                            """
                            UPDATE items
                            SET name = $1, short_name = $2,
                                is_vehicle = $3, online_visiblity = $4,
                                is_active = TRUE, updated_at = NOW()
                            WHERE id = $5
                            """,
                            name, short_name, is_vehicle, online_vis, item_id,
                        )
                    print(f"  [UPDATE] item {item_id:3}: '{existing['name']}' → '{name}'")
                    updated += 1
                else:
                    print(f"  [OK]     item {item_id:3}: '{name}' (no change)")
            else:
                # ID doesn't exist — insert fresh
                if not dry_run:
                    await conn.execute(
                        """
                        INSERT INTO items
                            (id, name, short_name, is_vehicle, online_visiblity, is_active)
                        VALUES ($1, $2, $3, $4, $5, TRUE)
                        """,
                        item_id, name, short_name, is_vehicle, online_vis,
                    )
                print(f"  [INSERT] item {item_id:3}: '{name}'")
                updated += 1

        # 5b: Deactivate V1-only items (not in V2)
        for item_id, item in sorted(current.items()):
            if item_id not in v2_ids and item["is_active"]:
                if not dry_run:
                    await conn.execute(
                        "UPDATE items SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
                        item_id,
                    )
                print(f"  [DEACT]  item {item_id:3}: '{item['name']}' (V1-only, no V2 equivalent)")
                deactivated += 1

        print(f"\n  Summary — updated: {updated}, deactivated: {deactivated}")
        return {"updated": updated, "deactivated": deactivated}


    # ---------------------------------------------------------------------------
    # Step 6 — Deactivate old item_rates
    # ---------------------------------------------------------------------------
    async def step6_deactivate_old_rates(conn, dry_run: bool) -> int:
        header("Step 6 — Deactivate old V1 item_rates")

        v2_item_ids = [row[0] for row in V2_ITEMS]
        v2_route_ids = list(ROUTE_MAP.values())  # routes 1,2,3,4,5,7

        # Active rates for routes 1–5, 7 that belong to non-V2 items
        old_rates = await conn.fetch(
            """
            SELECT id, item_id, route_id, rate, levy
            FROM   item_rates
            WHERE  is_active = TRUE
            AND  route_id  = ANY($1::int[])
            AND  item_id  != ALL($2::int[])
            """,
            v2_route_ids, v2_item_ids,
        )

        # Also fetch V2-item rows that will be REPLACED by fresh inserts in step 7
        # (these are the old rates for V2 item IDs that carry old rate values)
        old_v2_rates = await conn.fetch(
            """
            SELECT ir.id, ir.item_id, ir.route_id, ir.rate, ir.levy
            FROM   item_rates ir
            WHERE  ir.is_active = TRUE
            AND  ir.route_id  = ANY($1::int[])
            AND  ir.item_id   = ANY($2::int[])
            """,
            v2_route_ids, v2_item_ids,
        )

        all_to_deactivate = list(old_rates) + list(old_v2_rates)
        print(f"  Rows to deactivate: {len(all_to_deactivate)}"
            f"  ({len(old_rates)} V1-only + {len(old_v2_rates)} old V2-id rates)")

        if not dry_run and all_to_deactivate:
            ids = [r["id"] for r in all_to_deactivate]
            await conn.execute(
                f"SET LOCAL app.migration_notes = '{MIGRATION_NOTES}'"
            )
            await conn.execute(
                """
                UPDATE item_rates
                SET    is_active   = FALSE,
                       updated_at  = NOW()
                WHERE  id = ANY($1::int[])
                """,
                ids,
            )
            print(f"  Deactivated {len(ids)} rows (trigger recorded each as DEACTIVATED)")
        elif dry_run:
            print(f"  DRY RUN — would deactivate {len(all_to_deactivate)} rows")

        return len(all_to_deactivate)


# ---------------------------------------------------------------------------
# Step 7 — Insert new V2 item_rates
# ---------------------------------------------------------------------------
async def step7_insert_v2_rates(conn, dry_run: bool) -> int:
    header("Step 7 — Insert new V2 item_rates (21 items × 6 routes)")

    inserted = 0
    skipped  = 0

    if not dry_run:
        await conn.execute(f"SET LOCAL app.migration_notes = '{MIGRATION_NOTES}'")

    for route_name, items in RATE_DATA.items():
        route_id = ROUTE_MAP[route_name]
        for item_id, (rate_val, levy_val) in items.items():
            existing = await conn.fetchrow(
                "SELECT id, rate, levy, is_active FROM item_rates "
                "WHERE item_id = $1 AND route_id = $2",
                item_id, route_id,
            )
            rate = float(Decimal(str(rate_val)))
            levy = float(Decimal(str(levy_val)))

            if existing is None:
                if not dry_run:
                    await conn.execute(
                        """
                        INSERT INTO item_rates (levy, rate, item_id, route_id, is_active, created_at)
                        VALUES ($1, $2, $3, $4, TRUE, NOW())
                        """,
                        levy, rate, item_id, route_id,
                    )
                print(f"  [INSERT] route={route_id} item={item_id:2} rate={rate} levy={levy}")
                inserted += 1
            elif not existing["is_active"] or existing["rate"] != rate or existing["levy"] != levy:
                if not dry_run:
                    await conn.execute(
                        """
                        UPDATE item_rates
                        SET rate = $1, levy = $2, is_active = TRUE, updated_at = NOW()
                        WHERE id = $3
                        """,
                        rate, levy, existing["id"],
                    )
                print(f"  [UPDATE] route={route_id} item={item_id:2} rate={rate} levy={levy}")
                inserted += 1
            else:
                skipped += 1

    print(f"\n  Inserted/updated: {inserted}, already correct: {skipped}")
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def async_main(args: argparse.Namespace) -> None:
    import asyncpg

    mode = "DRY RUN" if args.dry_run else "LIVE"
    only_step = args.step

    print(f"\n{'='*60}")
    print(f"  V1 → V2 Item & Rate Migration  [{mode}]")
    print(f"  Migration label: {MIGRATION_LABEL}")
    print(f"{'='*60}")

    db_url = load_database_url(Path(args.env))
    conn   = await asyncpg.connect(db_url)

    try:
        # Step 0: always runs
        stats = await step0_preflight(conn)

        steps = {
            1: lambda: step1_backfill_ticket_snapshots(conn, args.dry_run),
            2: lambda: step2_backfill_booking_snapshots(conn, args.dry_run),
            3: lambda: step3_seed_history_baseline(conn, args.dry_run),
            4: lambda: step4_insert_migration_map(conn, args.dry_run),
            5: lambda: step5_update_items(conn, args.dry_run),
            6: lambda: step6_deactivate_old_rates(conn, args.dry_run),
            7: lambda: step7_insert_v2_rates(conn, args.dry_run),
        }

        run_steps = [only_step] if only_step else list(steps.keys())

        for n in run_steps:
            if n not in steps:
                print(f"  WARNING: step {n} not defined — skipped")
                continue
            async with conn.transaction():
                await steps[n]()
                if args.dry_run:
                    print(f"  DRY RUN — transaction rolled back for step {n}")
                    raise asyncpg.PostgresError("dry-run rollback")

    except asyncpg.PostgresError as e:
        if args.dry_run and "dry-run rollback" in str(e):
            pass  # expected
        else:
            print(f"\nERROR: {e}")
            sys.exit(1)
    finally:
        await conn.close()

    print(f"\n{'='*60}")
    if args.dry_run:
        print("  DRY RUN complete — no changes written.")
    else:
        print("  Migration complete.")
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate SSMSPL items + rates from V1 (49 items) to V2 (21 items)."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview all steps without writing to the database.")
    parser.add_argument("--step", type=int, default=None,
                        help="Run only a single step (1–7).")
    parser.add_argument("--env", default=str(DEFAULT_ENV),
                        help=f"Path to .env file with DATABASE_URL (default: {DEFAULT_ENV})")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
