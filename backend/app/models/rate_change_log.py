import uuid
from datetime import date, time, datetime

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, Numeric, Time, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RateChangeLog(Base):
    __tablename__ = "rate_change_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    route_id: Mapped[int] = mapped_column(Integer, ForeignKey("routes.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id"), nullable=False)
    old_rate: Mapped[float | None] = mapped_column(Numeric(38, 2), nullable=True)
    new_rate: Mapped[float | None] = mapped_column(Numeric(38, 2), nullable=True)
    updated_by_user: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RateChangeLog id={self.id} item_id={self.item_id} route_id={self.route_id}>"
