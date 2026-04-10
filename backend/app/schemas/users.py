from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreateByAdminRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=150)
    email: EmailStr
    area_id: int
    access_level_code: int = Field(ge=1, le=4)
    role_id: Optional[int] = None


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
