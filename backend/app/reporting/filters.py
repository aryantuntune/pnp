"""
Unified report filter model — single source of truth for all report parameters.

Every report function accepts a ReportFilters instance.  No report may invent
its own date/branch/route parameters independently.
"""
from __future__ import annotations

import datetime
from enum import Enum

from pydantic import BaseModel, model_validator


class DataSource(str, Enum):
    """Which data source(s) a report should query."""

    POS = "POS"
    PORTAL = "PORTAL"
    ALL = "ALL"


class ReportFilters(BaseModel):
    """
    Canonical filter object passed to every report function.

    Fields
    ------
    date_from       : Start of reporting window (inclusive).
    date_to         : End of reporting window (inclusive).  Must be >= date_from.
    branch_id       : Restrict to a single branch (optional).
    route_id        : Restrict to a single route (optional).
    payment_mode_id : Restrict to a single payment mode (optional).
                      Applied symmetrically to both POS and Portal; the FK
                      naturally means CASH/UPI filter excludes Portal rows and
                      ONLINE filter excludes POS rows.
    source          : Which data source(s) to include.  Defaults to ALL.
    """

    date_from: datetime.date
    date_to: datetime.date
    branch_id: int | None = None
    route_id: int | None = None
    payment_mode_id: int | None = None
    source: DataSource = DataSource.ALL

    @model_validator(mode="after")
    def _validate_date_range(self) -> "ReportFilters":
        if self.date_from > self.date_to:
            raise ValueError("date_from must be <= date_to")
        return self


def get_source_flags(filters: ReportFilters) -> tuple[bool, bool]:
    """
    Translate filters.source into (include_pos, include_portal) booleans.

    Every report calls this first and gates each query leg behind the
    corresponding flag.

    Returns
    -------
    (include_pos, include_portal)
    """
    if filters.source == DataSource.POS:
        return True, False
    if filters.source == DataSource.PORTAL:
        return False, True
    return True, True  # ALL
