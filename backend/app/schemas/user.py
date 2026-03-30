import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.rbac import UserRole
from app.core.validators import validate_password_complexity


class UserBase(BaseModel):
    email: EmailStr | None = Field(None, description="User's email address (optional)", examples=["admin@ssmspl.com"])
    username: str = Field(..., description="Unique login username", examples=["admin"])
    full_name: str = Field(..., description="User's full display name", examples=["System Administrator"])
    mobile_number: str | None = Field(None, max_length=20, description="User's mobile number (optional)", examples=["+919876543210"])
    role: UserRole = Field(
        default=UserRole.TICKET_CHECKER,
        description="RBAC role — determines menu access and permissions",
    )
    route_id: int | None = Field(None, description="Assigned route ID (FK to routes table)")


class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        description="Password (min 8 chars, must include uppercase, lowercase, digit, special char)",
        examples=["Password@123"],
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_complexity(v)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "newuser@ssmspl.com",
                    "username": "newuser",
                    "full_name": "New User",
                    "password": "Password@123",
                    "role": "ticket_checker",
                }
            ]
        }
    }


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, description="Updated display name")
    username: str | None = Field(
        None,
        min_length=4,
        max_length=50,
        description="Updated login username (unique, no spaces)",
        examples=["johndoe"],
    )
    email: EmailStr | None = Field(None, description="Updated email address")
    mobile_number: str | None = Field(None, max_length=20, description="Updated mobile number")
    role: UserRole | None = Field(None, description="Updated RBAC role")
    route_id: int | None = Field(None, description="Updated assigned route ID")
    is_active: bool | None = Field(None, description="Set false to deactivate the user")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is not None and " " in v:
            raise ValueError("Username must not contain spaces")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"full_name": "Updated Name", "username": "newname", "role": "manager", "route_id": 1}
            ]
        }
    }


class AdminResetPassword(BaseModel):
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password (min 8 chars, must include uppercase, lowercase, digit, special char)",
        examples=["NewPassword@123"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_complexity(v)


# SECURITY: Do NOT add hashed_password to this schema — it must never be serialized
class UserRead(UserBase):
    id: uuid.UUID = Field(..., description="Unique user identifier (UUID v4)")
    is_active: bool = Field(..., description="Whether the user account is active")
    is_verified: bool = Field(..., description="Whether the user's email is verified")
    route_name: str | None = Field(None, description="Display name of assigned route (e.g. 'Old Goa - Panaji')")
    last_login: datetime | None = Field(None, description="Timestamp of last successful login")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime | None = Field(None, description="Last profile update timestamp")

    model_config = {"from_attributes": True}


class ChangePassword(BaseModel):
    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password (min 8 chars, must include uppercase, lowercase, digit, special char)",
        examples=["NewPassword@123"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_complexity(v)


class RouteBranch(BaseModel):
    branch_id: int
    branch_name: str


class UserMeResponse(UserRead):
    menu_items: list[str] = Field(
        default=[],
        description="Role-based navigation menu items for the frontend sidebar",
        examples=[["Dashboard", "User Management", "Ferry Management"]],
    )
    route_branches: list[RouteBranch] = Field(
        default=[],
        description="Branches on the user's assigned route (for branch selection at login)",
    )
    active_branch_id: int | None = Field(
        default=None,
        description="Currently selected operating branch (set after login branch selection)",
    )
