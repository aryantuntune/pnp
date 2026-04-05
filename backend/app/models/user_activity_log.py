import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserActivityLog(Base):
    """Tracks individual user actions during a session.

    Used to audit what each user did: tickets created/viewed, reports
    generated, settings changed, etc.  Queried per-session for the
    admin sessions screen.
    """

    __tablename__ = "user_activity_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True,
    )

    __table_args__ = (
        Index("ix_user_activity_logs_session_action", "session_id", "action_type"),
    )

    def __repr__(self) -> str:
        return f"<UserActivityLog id={self.id} action={self.action_type} session={self.session_id}>"
