from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TwoFactorChallengeResponse(BaseModel):
    requires_2fa: bool = True
    session_token: str
    demo_otp: Optional[str] = None


class Verify2FARequest(BaseModel):
    session_token: str
    otp_code: str = Field(min_length=6, max_length=6)


class PermissionRead(BaseModel):
    code: str
    name: str

    class Config:
        orm_mode = True


class MeResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    status: str
    is_active: bool
    area_id: Optional[int]
    area_name: Optional[str]
    access_level_code: int
    access_level_name: str
    role_id: int
    role_name: str
    permissions: List[PermissionRead]


class ActivateAccountRequest(BaseModel):
    token: str = Field(min_length=16)
    password: str = Field(min_length=8, max_length=100)


class DemoActivationResponse(BaseModel):
    full_name: str
    email: EmailStr
    activation_link: str
