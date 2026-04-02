from pydantic import BaseModel, Field


class ActiveSessionRead(BaseModel):
    id: int = Field(..., description="Session row ID")
    user_id: str = Field(..., description="User UUID")
    session_id: str = Field(..., description="Session UUID")
    started_at: str | None = Field(None, description="Session start ISO timestamp")
    last_heartbeat: str | None = Field(None, description="Last heartbeat ISO timestamp")
    ip_address: str | None = Field(None, description="Client IP address")
    city: str | None = Field(None, description="City resolved from IP")
    user_agent: str | None = Field(None, description="Browser user-agent string")
    full_name: str = Field(..., description="User full name")
    username: str = Field(..., description="Username")
    role: str = Field(..., description="User role")
    ticket_count: int | None = Field(None, description="Tickets generated/verified during session (billing ops/checkers only)")


class SessionHistoryRead(ActiveSessionRead):
    ended_at: str | None = Field(None, description="Session end ISO timestamp")
    end_reason: str | None = Field(None, description="How session ended: logout, timeout, login_elsewhere")
