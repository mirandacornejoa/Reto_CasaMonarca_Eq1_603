from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: Optional[int]
    action: str
    resource: str
    resource_id: Optional[str]
    result: str
    detail: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
