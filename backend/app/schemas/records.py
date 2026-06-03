"""Schemas de registros de migrantes — formulario real de entrevista de ingreso."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    # ── Campos del formulario real ──
    attention_date: Optional[date] = None
    first_name: str = Field(min_length=1, max_length=100)
    last_name_1: str = Field(min_length=1, max_length=100)
    last_name_2: Optional[str] = Field("X", max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    gender: Optional[str] = Field(None, max_length=50)
    country_of_origin: Optional[str] = Field(None, max_length=100)
    state_department: Optional[str] = Field(None, max_length=100)
    civil_status: Optional[str] = Field(None, max_length=30)
    birth_date: Optional[date] = None
    age_range: Optional[str] = Field(None, max_length=30)
    population_group: Optional[str] = Field(None, max_length=60)
    observations: Optional[str] = None
    # ── Campos legacy (compatibilidad) ──
    name_or_alias: Optional[str] = Field(None, max_length=200)
    nationality: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=80)
    contact_info: Optional[str] = Field(None, max_length=255)
    needs: Optional[List[str]] = None
    registration_date: Optional[datetime] = None
    area_id: Optional[int] = None
    status: str = Field("REGISTRADO", max_length=30)
    template_id: Optional[int] = None


class ChannelRequest(BaseModel):
    notes: Optional[str] = None


class RecordApprove(BaseModel):
    """Body opcional para el endpoint review. Firma requerida para niveles 1-2."""
    content_hash: Optional[str] = None
    signature_b64: Optional[str] = None


class RecordUpdate(BaseModel):
    # Firma digital — requerida para niveles 1-2
    content_hash: Optional[str] = None
    signature_b64: Optional[str] = None
    attention_date: Optional[date] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name_1: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name_2: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    gender: Optional[str] = Field(None, max_length=50)
    country_of_origin: Optional[str] = Field(None, max_length=100)
    state_department: Optional[str] = Field(None, max_length=100)
    civil_status: Optional[str] = Field(None, max_length=30)
    birth_date: Optional[date] = None
    age_range: Optional[str] = Field(None, max_length=30)
    population_group: Optional[str] = Field(None, max_length=60)
    observations: Optional[str] = None
    # Legacy
    name_or_alias: Optional[str] = Field(None, min_length=1, max_length=200)
    nationality: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=80)
    contact_info: Optional[str] = Field(None, max_length=255)
    needs: Optional[List[str]] = None
    area_id: Optional[int] = None
    status: Optional[str] = Field(None, max_length=30)


class RecordRead(BaseModel):
    id: int
    folio: Optional[str]
    # Formulario real
    attention_date: Optional[date] = None
    first_name: Optional[str] = None
    last_name_1: Optional[str] = None
    last_name_2: Optional[str] = None
    phone: Optional[str] = None
    country_of_origin: Optional[str] = None
    state_department: Optional[str] = None
    civil_status: Optional[str] = None
    birth_date: Optional[date] = None
    population_group: Optional[str] = None
    # Legacy
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
    # Workflow
    workflow_status: Optional[str] = "pendiente"
    assigned_operator_id: Optional[int] = None
    assigned_operator_name: Optional[str] = None
    assigned_coordinator_id: Optional[int] = None
    assigned_coordinator_name: Optional[str] = None
    channeled_at: Optional[datetime] = None
    channel_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    # Anonimización ARCO
    is_anonymized: bool = False
    anonymized_at: Optional[datetime] = None
    # Petición de eliminación activa (para mostrar en UI)
    pending_deletion_folio: Optional[str] = None
    pending_deletion_by: Optional[str] = None
    # Autoría
    created_by_id: Optional[int]
    created_by_name: Optional[str] = None
    updated_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
