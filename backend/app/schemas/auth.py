from typing import Optional
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=50)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserBrief"


class UserBrief(BaseModel):
    id: int
    nickname: str
    avatar_url: Optional[str] = None
    membership_tier: str = "free"
    role: str = "user"

    model_config = {"from_attributes": True}
