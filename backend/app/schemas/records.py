from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    name_or_alias: str = Field(min_length=1, max_length=200)
    nationality: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=80)
    age_range: Optional[str] = Field(None, max_length=30)
    gender: Optional[str] = Field(None, max_length=50)
    contact_info: Optional[str] = Field(None, max_length=255)
    needs: Optional[List[str]] = None
    registration_date: Optional[datetime] = None
    observations: Optional[str] = None
    area_id: Optional[int] = None
    status: str = Field("REGISTRADO", max_length=30)
    template_id: Optional[int] = None


class RecordUpdate(BaseModel):
    name_or_alias: Optional[str] = Field(None, min_length=1, max_length=200)
    nationality: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=80)
    age_range: Optional[str] = Field(None, max_length=30)
    gender: Optional[str] = Field(None, max_length=50)
    contact_info: Optional[str] = Field(None, max_length=255)
    needs: Optional[List[str]] = None
    observations: Optional[str] = None
    area_id: Optional[int] = None
    status: Optional[str] = Field(None, max_length=30)


class RecordRead(BaseModel):
    id: int
    folio: Optional[str]
    name_or_alias: str
    nationality: Optional[str]
    language: Optional[str]
    age_range: Optional[str]
    gender: Optional[str]
    contact_info: Optional[str]
    needs: Optional[List[str]]
    registration_date: datetime
    observations: Optional[str]
    area_id: Optional[int]
    area_name: Optional[str] = None
    status: str
    template_id: Optional[int]
    sha256_hash: Optional[str]
    created_by_id: Optional[int]
    created_by_name: Optional[str] = None
    updated_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
