from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TemplateFieldDef(BaseModel):
    name: str
    label: str
    field_type: str = "text"  # text, select, multiselect, textarea, date, number
    required: bool = False
    options: Optional[List[str]] = None
    placeholder: Optional[str] = None


class TemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    fields: List[TemplateFieldDef]


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    fields: Optional[List[TemplateFieldDef]] = None


class TemplateStatusUpdate(BaseModel):
    is_active: bool


class TemplateRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    fields_json: str
    is_active: bool
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
