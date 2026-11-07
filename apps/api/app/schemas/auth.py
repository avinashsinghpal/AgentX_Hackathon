from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SellerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    store_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    store_url: str | None = Field(default=None, max_length=512)


class BuyerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    full_name: str
    phone: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    user: UserResponse
    redirect_uri: str
    csrf_token: str
    token: str | None = None  # Returned for mobile/testing clients
    tenant_info: dict[str, Any] | None = None
