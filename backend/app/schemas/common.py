from datetime import datetime

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class Timestamped(BaseModel):
    created_at: datetime

    class Config:
        orm_mode = True
