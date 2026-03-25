"""
Generic merge helper for combining POS and Portal query results.

Pattern used by every report:
  1. Run POS query  → list[dict]
  2. Run Portal query → list[dict]
  3. Call merge_by_key(pos_data, portal_data, key_fn) → unified list[dict]
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

_NUMERIC = (int, float, Decimal)


def merge_by_key(
    pos_data: list[dict],
    portal_data: list[dict],
    key_fn: Callable[[dict], Any],
    skip_sum: frozenset[str] = frozenset(),
) -> list[dict]:
    """
    Merge two lists of row-dicts by a grouping key, summing numeric fields.

    Both lists are combined and grouped by ``key_fn(row)``.  For rows that
    share the same key, all ``int``, ``float``, and ``Decimal`` fields are
    summed.  Non-numeric fields (strings, dates, booleans) are kept from the
    *first* row seen for that key.

    Parameters
    ----------
    pos_data    : Rows from the POS query leg.
    portal_data : Rows from the Portal query leg.
    key_fn      : Callable that extracts a hashable merge key from a row dict.
                  Can return a scalar or a tuple for composite keys.
    skip_sum    : Set of field names that are numeric but must NOT be summed.
                  Use this when the grouping key itself is an integer column
                  (e.g. ``payment_mode_id``) to prevent ``1 + 1 = 2``.

    Returns
    -------
    List of merged dicts, one entry per unique key.  Order follows insertion
    order (POS rows processed before Portal rows).

    Example
    -------
    >>> pos    = [{"date": "2026-01-01", "amount": 100.0, "count": 2}]
    >>> portal = [{"date": "2026-01-01", "amount": 250.0, "count": 3}]
    >>> merge_by_key(pos, portal, key_fn=lambda r: r["date"])
    [{"date": "2026-01-01", "amount": 350.0, "count": 5}]
    """
    buckets: dict[Any, dict] = {}

    for row in pos_data + portal_data:
        key = key_fn(row)
        if key not in buckets:
            buckets[key] = dict(row)
        else:
            for field, value in row.items():
                if isinstance(value, _NUMERIC) and field not in skip_sum:
                    buckets[key][field] = buckets[key].get(field, 0) + value

    return list(buckets.values())
