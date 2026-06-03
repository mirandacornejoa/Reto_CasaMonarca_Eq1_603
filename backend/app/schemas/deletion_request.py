"""Schemas para solicitudes de eliminación."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeletionRequestCreate(BaseModel):
    record_id: int
    reason: str = Field(min_length=1)


class DeletionRequestReview(BaseModel):
    action: str  # 'approve' o 'reject'
    notes: Optional[str] = None
    content_hash: Optional[str] = None
    signature_b64: Optional[str] = None


class DeletionRequestRead(BaseModel):
    id: int
    folio: Optional[str] = None
    record_id: int
    record_folio: Optional[str] = None
    record_name: Optional[str] = None
    requested_by_id: int
    requested_by_name: Optional[str] = None
    reason: str
    status: str
    reviewed_by_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True
