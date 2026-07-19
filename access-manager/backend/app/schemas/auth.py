from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.password_policy import validate_user_password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_user_password(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
