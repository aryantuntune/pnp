from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.validators import validate_password_complexity


class LoginRequest(BaseModel):
    username: str = Field(..., description="The user's login username", examples=["admin"])
    password: str = Field(..., description="The user's password", examples=["Password@123"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"username": "admin", "password": "Password@123"}
            ]
        }
    }


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="A valid refresh token from a previous login or refresh")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
            ]
        }
    }


class TokenPayload(BaseModel):
    sub: str = Field(..., description="Subject — the user's UUID")
    type: str = Field(..., description="Token type: 'access' or 'refresh'")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address associated with the account")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Password reset token from the email link")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars, must include uppercase, lowercase, digit, special char)")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_complexity(v)


class MobileUserInfo(BaseModel):
    id: str = Field(..., description="User UUID")
    full_name: str
    email: str | None = None
    role: str
    route_id: int | None = None
    route_name: str | None = None


class MobileLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: MobileUserInfo
