"""
Background task: auto-cancel PENDING bookings older than 15 minutes.
Runs every 5 minutes via asyncio loop started at app startup.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.booking import Booking
from app.models.booking_item import BookingItem

logger = logging.getLogger("ssmspl.booking_expiry")

EXPIRY_MINUTES = 15
CHECK_INTERVAL_SECONDS = 300  # 5 minutes


async def cancel_expired_bookings() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=EXPIRY_MINUTES)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Booking).where(
                    Booking.status == "PENDING",
                    Booking.created_at < cutoff,
                )
            )
            stale = result.scalars().all()
            if not stale:
                return 0
            for booking in stale:
                booking.status = "CANCELLED"
                booking.is_cancelled = True
                items_result = await db.execute(
                    select(BookingItem).where(BookingItem.booking_id == booking.id)
                )
                for item in items_result.scalars().all():
                    item.is_cancelled = True
            await db.commit()
            logger.info("Auto-cancelled %d expired PENDING bookings", len(stale))
            return len(stale)
        except Exception:
            await db.rollback()
            logger.exception("Error cancelling expired bookings")
            return 0


async def expiry_loop():
    while True:
        await cancel_expired_bookings()
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
