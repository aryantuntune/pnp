#!/usr/bin/env python3
"""
Seed Route Item Rates  (PDF: "NEW ITEM ID & RATE")
===================================================
Hardcoded from the official rate sheet PDF:
    data/item_rates/NEW ITEM ID & RATE.pdf

Upserts item_rates for routes 1–5 and 7.
Route 6 (AMBET ↔ MHAPRAL) is NOT in the PDF — left untouched.

Usage:
    python scripts/seed_route_item_rates.py                # execute changes
    python scripts/seed_route_item_rates.py --dry-run       # preview only
    python scripts/seed_route_item_rates.py --env .env.production
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# PDF item number  →  DB item_id
#
# The PDF defines 21 canonical items (numbered 1–21).
# This map translates each PDF item number to its matching row in the `items`
# table.  Where the PDF merges multiple old items into one row the closest
# DB item is used (noted below).
# ---------------------------------------------------------------------------
PDF_TO_DB_ITEM: dict[int, int] = {
    1:  1,   # CYCLE
    2:  2,   # MOTOR CYCLE WITH DRIVER
    3:  3,   # EMPTY 3 WHLR RICKSHAW
    4:  7,   # MAGIC / IRIS / CAR  →  EMPTY CAR 5 ST (item 7)
    5:  8,   # LUX CAR / SUMO / SCORPIO / TAVERA 7 ST  →  EMPTY LUX. CAR 5 ST (item 8)
    6:  13,  # AMBULANCE
    7:  18,  # T.T / 407 / 709 / 18 & 21 ST BUS  →  MED. GOODS 6 WHLR 709 (item 18)
    8:  21,  # BUS / TRUCK / TANKER  →  TANKER/TRUCK (item 21)
    9:  22,  # TRUCK 10 WHLR / JCB  →  TRUCK 10 WHLR (item 22)
    10: 33,  # TRACTOR WITH TROLLY
    11: 11,  # PASSENGER ADULT ABOVE 12 YR
    12: 12,  # PASSENGER CHILD 3-12 YR
    13: 23,  # GOODS PER HALF TON
    14: 24,  # PASS LUG ABV 20 KG PER KG
    15: 31,  # DOG/GOATS/SHEEP & FISH/CHICKEN/BIRDS/FRUITS  →  FISH/CHICKEN/BIRDS/FRUITS (item 31)
    16: 26,  # COWS / BUFFELLOW (PER NO)
    17: 29,  # TOURIST (FOR 1 HOUR)
    18: 27,  # MONTH PASS STUDENT UPTO 7TH  →  MONTH PASS STDNT UPTO 10TH (item 27)
    19: 28,  # MONTH PASS STUDENT ABOVE XTH
    20: 30,  # MONTH PASS PASSENGER
    21: 34,  # SPECIAL FERRY
}

# Display labels (English)
ITEM_NAMES: dict[int, str] = {
    1:  "Cycle",
    2:  "Motor Cycle With Driver",
    3:  "Empty 3-Wheeler Rickshaw",
    4:  "Magic / Iris / Car",
    5:  "Lux Car / Sumo / Scorpio / Tavera 7 St",
    6:  "Ambulance",
    7:  "T.T / 407 / 709 / 18 & 21 St Bus",
    8:  "Bus / Truck / Tanker",
    9:  "Truck 10 Whlr / JCB",
    10: "Tractor With Trolly",
    11: "Passenger Adult Above 12 Yr",
    12: "Passenger Child 3-12 Yr",
    13: "Goods Per Half Ton",
    14: "Pass Lug Abv 20 Kg Per Kg",
    15: "Dog/Goats/Sheep & Fish/Chicken/Birds/Fruits",
    16: "Cows / Buffellow (Per No)",
    17: "Tourist (For 1 Hour)",
    18: "Month Pass Student Upto 7th",
    19: "Month Pass Student Above Xth",
    20: "Month Pass Passenger",
    21: "Special Ferry",
}

# Route name  →  DB route_id
ROUTE_MAP: dict[str, int] = {
    "DABHOL-DHOPAVE":    1,
    "VESHVI-BAGMANDALE": 2,
    "JAIGAD-TAVSAL":     3,
    "DIGHI-AGARDANDA":   4,
    "VASAI-BHAYANDAR":   5,
    "VIRAR-SAFALE":      7,
}

# ---------------------------------------------------------------------------
# Rate data
# Source: PDF "NEW ITEM ID & RATE"
# Format: {route_name: {pdf_item_no: (rate, levy)}}
# ---------------------------------------------------------------------------
RATE_DATA: dict[str, dict[int, tuple[int, int]]] = {
    # --------------------------------------------------------
    # ROUTE 1 — DABHOL ↔ DHOPAVE
    # --------------------------------------------------------
    "DABHOL-DHOPAVE": {
        1:  (13,   2),   # Cycle
        2:  (58,   7),   # Motor Cycle With Driver
        3:  (81,   9),   # Empty 3-Wheeler Rickshaw
        4:  (163, 17),   # Magic/Iris/Car
        5:  (181, 19),   # Lux Car/Sumo/Scorpio/Tavera 7 St
        6:  (180,  0),   # Ambulance
        7:  (225, 25),   # T.T/407/709/18 & 21 St Bus
        8:  (360, 40),   # Bus/Truck/Tanker
        9:  (500, 50),   # Truck 10 Whlr/JCB
        10: (319, 31),   # Tractor With Trolly
        11: (18,   2),   # Passenger Adult Above 12 Yr
        12: (9,    1),   # Passenger Child 3-12 Yr
        13: (36,   4),   # Goods Per Half Ton
        14: (1,    0),   # Pass Lug Abv 20 Kg Per Kg
        15: (18,   2),   # Dog/Goats/Sheep & Fish/Chicken/Birds/Fruits
        16: (45,   5),   # Cows/Buffellow (Per No)
        17: (27,   3),   # Tourist (For 1 Hour)
        18: (270, 30),   # Month Pass Student Upto 7th
        19: (360, 40),   # Month Pass Student Above Xth
        20: (640, 60),   # Month Pass Passenger
        21: (500,  0),   # Special Ferry
    },
    # --------------------------------------------------------
    # ROUTE 2 — VESHVI ↔ BAGMANDALE
    # --------------------------------------------------------
    "VESHVI-BAGMANDALE": {
        1:  (13,   2),
        2:  (58,   7),
        3:  (81,   9),
        4:  (163, 17),
        5:  (181, 19),
        6:  (180,  0),
        7:  (225, 25),
        8:  (360, 40),
        9:  (500, 50),
        10: (319, 31),
        11: (18,   2),
        12: (9,    1),
        13: (36,   4),
        14: (1,    0),
        15: (18,   2),
        16: (45,   5),
        17: (27,   3),
        18: (270, 30),
        19: (360, 40),
        20: (640, 60),
        21: (500,  0),
    },
    # --------------------------------------------------------
    # ROUTE 3 — JAIGAD ↔ TAVSAL
    # --------------------------------------------------------
    "JAIGAD-TAVSAL": {
        1:  (18,   2),
        2:  (73,   7),
        3:  (95,  10),
        4:  (182, 18),
        5:  (205, 20),
        6:  (200,  0),
        7:  (238, 22),
        8:  (410, 40),
        9:  (550, 50),
        10: (273, 27),
        11: (27,   3),
        12: (13,   2),
        13: (45,   5),
        14: (1,    0),
        15: (23,   2),
        16: (64,   6),
        17: (45,   5),
        18: (450, 50),
        19: (550, 50),
        20: (1180, 120),
        21: (600,  0),
    },
    # --------------------------------------------------------
    # ROUTE 4 — DIGHI ↔ AGARDANDA
    # --------------------------------------------------------
    "DIGHI-AGARDANDA": {
        1:  (10,   1),
        2:  (50,   5),
        3:  (68,   7),
        4:  (140, 14),
        5:  (160, 16),
        6:  (200,  0),
        7:  (200, 20),
        8:  (300, 30),
        9:  (400, 50),
        10: (200, 20),
        11: (27,   3),
        12: (13,   2),
        13: (30,   3),
        14: (1,    0),
        15: (9,    1),
        16: (50,   5),
        17: (45,   5),
        18: (450, 50),
        19: (550, 50),
        20: (1180, 120),
        21: (700,  0),
    },
    # --------------------------------------------------------
    # ROUTE 5 — VASAI ↔ BHAYANDAR
    # --------------------------------------------------------
    "VASAI-BHAYANDAR": {
        1:  (9,    1),
        2:  (60,   6),
        3:  (100, 10),
        4:  (180, 20),
        5:  (180, 20),
        6:  (200,  0),
        7:  (200, 20),
        8:  (300, 30),
        9:  (500, 50),
        10: (200, 20),
        11: (27,   3),
        12: (13,   2),
        13: (27,   3),
        14: (1,    0),
        15: (36,   4),
        16: (50,   5),
        17: (55,   5),
        18: (450, 50),
        19: (550, 50),
        20: (1000, 100),
        21: (500,  0),
    },
    # --------------------------------------------------------
    # ROUTE 7 — VIRAR ↔ SAFALE
    # --------------------------------------------------------
    "VIRAR-SAFALE": {
        1:  (9,    1),
        2:  (60,   6),
        3:  (100, 10),
        4:  (180, 20),
        5:  (180, 20),
        6:  (200,  0),
        7:  (200, 20),
        8:  (300, 30),
        9:  (500, 50),
        10: (200, 20),
        11: (27,   3),
        12: (13,   2),
        13: (27,   3),
        14: (1,    0),
        15: (10,   1),
        16: (50,   5),
        17: (55,   5),
        18: (550, 50),
        19: (600, 50),
        20: (1000, 100),
        21: (500,  0),
    },
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class RateEntry:
    route_name: str
    route_id: int
    pdf_item_no: int
    item_id: int
    rate: Decimal
    levy: Decimal

    @property
    def label(self) -> str:
        return ITEM_NAMES.get(self.pdf_item_no, f"Item #{self.pdf_item_no}")


@dataclass
class RouteResult:
    route_name: str
    added: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Build flat list of RateEntry from RATE_DATA
# ---------------------------------------------------------------------------
def build_entries() -> list[RateEntry]:
    entries: list[RateEntry] = []
    for route_name, items in RATE_DATA.items():
        route_id = ROUTE_MAP[route_name]
        for pdf_no, (rate_val, levy_val) in items.items():
            item_id = PDF_TO_DB_ITEM.get(pdf_no)
            if item_id is None:
                print(f"  WARNING: No DB item_id mapping for PDF item #{pdf_no} — skipped")
                continue
            entries.append(RateEntry(
                route_name=route_name,
                route_id=route_id,
                pdf_item_no=pdf_no,
                item_id=item_id,
                rate=Decimal(str(rate_val)),
                levy=Decimal(str(levy_val)),
            ))
    return entries


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
SCRIPT_DIR  = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent

_ENV_CANDIDATES = [
    BACKEND_DIR / ".env.production",
    BACKEND_DIR / ".env.development",
]
DEFAULT_ENV = next((p for p in _ENV_CANDIDATES if p.exists()), BACKEND_DIR / ".env.development")


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


async def upsert_rates(
    entries: list[RateEntry],
    db_url: str,
    dry_run: bool,
) -> list[RouteResult]:
    import asyncpg

    conn = await asyncpg.connect(db_url)
    results: dict[str, RouteResult] = {}

    try:
        # Tag all writes so the audit trigger records the source
        if not dry_run:
            await conn.execute("SET LOCAL app.migration_notes = 'RATE_SEED_UPDATE'")

        for entry in entries:
            if entry.route_name not in results:
                results[entry.route_name] = RouteResult(route_name=entry.route_name)
            result = results[entry.route_name]

            existing = await conn.fetchrow(
                "SELECT id, rate, levy FROM item_rates "
                "WHERE item_id = $1 AND route_id = $2",
                entry.item_id, entry.route_id,
            )

            if existing is None:
                if not dry_run:
                    await conn.execute(
                        "INSERT INTO item_rates (levy, rate, item_id, route_id, is_active, created_at) "
                        "VALUES ($1, $2, $3, $4, TRUE, NOW())",
                        float(entry.levy), float(entry.rate),
                        entry.item_id, entry.route_id,
                    )
                result.added += 1
                print(f"  [ADD]  {entry.route_name} | {entry.label} | "
                      f"rate={entry.rate} levy={entry.levy}"
                      f"{' (DRY RUN)' if dry_run else ''}")

            else:
                existing_rate = Decimal(str(existing["rate"])) if existing["rate"] is not None else None
                existing_levy = Decimal(str(existing["levy"])) if existing["levy"] is not None else None

                if existing_rate != entry.rate or existing_levy != entry.levy:
                    if not dry_run:
                        await conn.execute(
                            "UPDATE item_rates SET rate = $1, levy = $2, is_active = TRUE, "
                            "updated_at = NOW() WHERE id = $3",
                            float(entry.rate), float(entry.levy), existing["id"],
                        )
                    changes = []
                    if existing_rate != entry.rate:
                        changes.append(f"rate: {existing_rate}→{entry.rate}")
                    if existing_levy != entry.levy:
                        changes.append(f"levy: {existing_levy}→{entry.levy}")
                    result.updated += 1
                    print(f"  [UPD]  {entry.route_name} | {entry.label} | "
                          f"{', '.join(changes)}"
                          f"{' (DRY RUN)' if dry_run else ''}")
                else:
                    result.skipped += 1

    finally:
        await conn.close()

    return list(results.values())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def async_main(args: argparse.Namespace) -> None:
    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"\n{'='*60}")
    print(f"  Seed Route Item Rates  [{mode}]")
    print(f"  Source: PDF — NEW ITEM ID & RATE")
    print(f"{'='*60}")
    print(f"  Env : {args.env}\n")

    entries = build_entries()
    print(f"Prepared {len(entries)} item-rate entries across {len(RATE_DATA)} routes.\n")

    db_url = load_database_url(Path(args.env))
    print("Connecting to database...")
    route_results = await upsert_rates(entries, db_url, args.dry_run)

    print(f"\n{'='*60}")
    print("  Per-Route Summary")
    print(f"{'='*60}")
    total_added = total_updated = total_skipped = 0
    for r in route_results:
        print(f"  {r.route_name}")
        print(f"    Added:   {r.added}")
        print(f"    Updated: {r.updated}")
        print(f"    Skipped: {r.skipped}")
        total_added   += r.added
        total_updated += r.updated
        total_skipped += r.skipped
        for err in r.errors:
            print(f"    ERROR: {err}")

    print(f"\n{'='*60}")
    print("  Grand Summary")
    print(f"{'='*60}")
    print(f"  Routes processed : {len(route_results)}")
    print(f"  Total added      : {total_added}")
    print(f"  Total updated    : {total_updated}")
    print(f"  Total skipped    : {total_skipped}")
    if args.dry_run:
        print(f"\n  ** DRY RUN — no changes written to the database **")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed route-wise item rates from the new PDF rate sheet."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing to the database.")
    parser.add_argument("--env", default=str(DEFAULT_ENV),
                        help=f"Path to .env file with DATABASE_URL (default: {DEFAULT_ENV})")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
