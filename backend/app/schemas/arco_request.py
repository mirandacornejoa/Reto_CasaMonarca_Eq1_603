"""Schemas de solicitudes ARCO (Acceso, Rectificación, Cancelación, Oposición)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


VALID_TYPES = {"ACCESS", "RECTIFICATION", "CANCELLATION", "OPPOSITION"}
VALID_STATUSES = {"PENDING", "IN_REVIEW", "ESCALATED", "COMPLETED", "APPROVED", "REJECTED"}


class ArcoRequestCreate(BaseModel):
    request_type: str = Field(..., description="ACCESS | RECTIFICATION | CANCELLATION | OPPOSITION")
    record_id: int
    reason: str = Field(..., min_length=1)
    description: Optional[str] = None
    # JSON libre con los campos a corregir (solo RECTIFICATION)
    requested_changes_json: Optional[str] = None


class ArcoRequestAttend(BaseModel):
    """Coordinador atiende ACCESS / OPPOSITION / RECTIFICATION."""
    resolution_notes: Optional[str] = None
    content_hash: Optional[str] = None
    signature_b64: Optional[str] = None


class ArcoRequestEscalate(BaseModel):
    """Coordinador escala CANCELLATION al admin."""
    notes: Optional[str] = None


class ArcoRequestReview(BaseModel):
    """Admin aprueba o rechaza CANCELLATION."""
    action: str = Field(..., description="approve | reject")
    resolution_notes: Optional[str] = None
    content_hash: Optional[str] = None
    signature_b64: Optional[str] = None


class ArcoRequestRead(BaseModel):
    id: int
    folio: Optional[str] = None
    request_type: str
    status: str
    record_id: Optional[int] = None
    record_folio: Optional[str] = None
    record_name: Optional[str] = None
    requested_by_id: int
    requested_by_name: Optional[str] = None
    assigned_coordinator_id: Optional[int] = None
    assigned_coordinator_name: Optional[str] = None
    assigned_admin_id: Optional[int] = None
    assigned_admin_name: Optional[str] = None
    reason: str
    description: Optional[str] = None
    requested_changes_json: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        orm_mode = True
