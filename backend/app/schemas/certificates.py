from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CertificateRead(BaseModel):
    id: int
    user_id: int
    serial_number: str
    status: str
    fingerprint: str
    issued_at: datetime
    expires_at: datetime
    created_at: datetime

    class Config:
        orm_mode = True


class CertificatePublicRead(BaseModel):
    """Vista limitada para usuarios externos."""
    id: int
    serial_number: str
    status: str
    fingerprint: str
    issued_at: datetime
    expires_at: datetime

    class Config:
        orm_mode = True


class CertificateValidationResponse(BaseModel):
    serial_number: str
    status: str
    is_valid: bool
    issued_at: datetime
    expires_at: datetime
    message: str
