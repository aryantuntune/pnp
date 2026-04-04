from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyReportLog(Base):
    """Tracks which dates a daily report was successfully sent.

    Used to prevent duplicate sends when multiple gunicorn workers each run
    their own daily_report_loop.  The UNIQUE constraint on report_date
    guarantees at-most-once delivery per day.
    """

    __tablename__ = "daily_report_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sending")

    def __repr__(self) -> str:
        return f"<DailyReportLog date={self.report_date} status={self.status}>"
