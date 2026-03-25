"""
Reusable sorting helpers for report output rows.

All functions accept and return a list[dict].  They do not mutate the input.
Use these consistently so every report presents data in the same order.
"""
from __future__ import annotations

import datetime


def sort_by_date(data: list[dict], date_key: str = "date") -> list[dict]:
    """
    Sort rows ascending by a date field.

    Parameters
    ----------
    data     : List of row dicts.
    date_key : Name of the date field (default: ``"date"``).
    """
    return sorted(data, key=lambda r: r[date_key])


def sort_by_item_name(data: list[dict], name_key: str = "item_name") -> list[dict]:
    """
    Sort rows alphabetically ascending by item name (case-insensitive).

    Parameters
    ----------
    data     : List of row dicts.
    name_key : Name of the item name field (default: ``"item_name"``).
    """
    return sorted(data, key=lambda r: r[name_key].lower())


def sort_by_departure_then_item(
    data: list[dict],
    departure_key: str = "departure",
    item_key: str = "item_name",
) -> list[dict]:
    """
    Sort rows by departure time ascending, nulls last, then by item name
    ascending (case-insensitive).

    Null-departure rows represent walk-in / open-schedule trips and always
    appear after all time-assigned ferry slots.

    Parameters
    ----------
    data          : List of row dicts.
    departure_key : Name of the departure field (default: ``"departure"``).
    item_key      : Name of the item name field (default: ``"item_name"``).
    """
    return sorted(
        data,
        key=lambda r: (
            r[departure_key] is None,  # False (0) < True (1) → non-null sorts first
            r[departure_key] or datetime.time(0, 0),
            r[item_key].lower(),
        ),
    )


def sort_by_payment_mode(
    data: list[dict],
    mode_key: str = "payment_mode_name",
) -> list[dict]:
    """
    Sort rows alphabetically ascending by payment mode name (case-insensitive).

    Parameters
    ----------
    data     : List of row dicts.
    mode_key : Name of the payment mode field (default: ``"payment_mode_name"``).
    """
    return sorted(data, key=lambda r: r[mode_key].lower())
