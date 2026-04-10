from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_active_user
from app.repositories.role_repository import RoleRepository
from app.schemas.roles import AccessLevelSchema, PermissionSchema, RoleSchema

router = APIRouter()


@router.get("/", response_model=List[RoleSchema])
def list_roles(
    db: Session = Depends(get_db),
    _: object = Depends(require_active_user),
):
    roles = RoleRepository.list_roles(db)
    response: List[RoleSchema] = []
    for role in roles:
        response.append(
            RoleSchema(
                id=role.id,
                name=role.name,
                description=role.description,
                area_scoped=role.area_scoped,
                access_level_code=role.access_level.code,
                permissions=role.permissions,
            )
        )
    return response


@router.get("/permissions", response_model=List[PermissionSchema])
def list_permissions(
    db: Session = Depends(get_db),
    _: object = Depends(require_active_user),
):
    return RoleRepository.list_permissions(db)


@router.get("/levels", response_model=List[AccessLevelSchema])
def list_levels(
    db: Session = Depends(get_db),
    _: object = Depends(require_active_user),
):
    return RoleRepository.list_levels(db)
