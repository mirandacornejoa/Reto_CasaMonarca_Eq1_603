"""Schemas para dashboard por perfil."""

from typing import List, Optional

from pydantic import BaseModel


class DashboardStats(BaseModel):
    role: str
    level_code: int = 0
    area_name: Optional[str] = None
    total_records: int = 0
    pending_records: int = 0
    reviewed_records: int = 0
    channeled_records: int = 0
    closed_records: int = 0
    pending_deletion_requests: int = 0
    my_records: int = 0
    assigned_to_me: int = 0
    recent_records: List[dict] = []
    pending_deletions: List[dict] = []
