from typing import List, Optional

from pydantic import BaseModel


class PermissionSchema(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]

    class Config:
        orm_mode = True


class RoleSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    area_scoped: bool
    access_level_code: int
    permissions: List[PermissionSchema]

    class Config:
        orm_mode = True


class AccessLevelSchema(BaseModel):
    id: int
    code: int
    name: str
    description: Optional[str]

    class Config:
        orm_mode = True
