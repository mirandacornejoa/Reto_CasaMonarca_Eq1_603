from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: Optional[int]
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    resource: str
    resource_id: Optional[str]
    result: str
    detail: Optional[str]
    hash_related: Optional[str]
    certificate_id: Optional[int]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
