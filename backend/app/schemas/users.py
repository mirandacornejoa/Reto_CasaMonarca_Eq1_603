from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreateByAdminRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=150)
    email: EmailStr
    area_id: int
    access_level_code: int = Field(ge=1, le=4)
    role_id: Optional[int] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class UserRead(BaseModel):
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
    starts_at: Optional[datetime]
    expires_at: Optional[datetime]
    certificate_id: Optional[int] = None
    certificate_status: Optional[str] = None
    certificate_serial: Optional[str] = None
    certificate_expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True


class UserCreateByAdminResponse(BaseModel):
    user: UserRead
    activation_link: Optional[str] = None
    activation_expires_in_hours: int


class UserLevelUpdateRequest(BaseModel):
    access_level_code: int = Field(ge=1, le=4)
    role_id: Optional[int] = None
    area_id: Optional[int] = None


class UserStatusUpdateRequest(BaseModel):
    is_active: bool


class UserExpiryUpdateRequest(BaseModel):
    starts_at: Optional[datetime] = None
    expires_at: datetime


class AreaRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool

    class Config:
        orm_mode = True


class AccessLevelRead(BaseModel):
    id: int
    code: int
    name: str
    description: Optional[str]

    class Config:
        orm_mode = True
