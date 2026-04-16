"""Rutas de usuarios — proxy ligero que redirige a identity para retrocompatibilidad."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.mappers import to_user_read
from app.core.database import get_db
from app.core.deps import require_admin
from app.repositories.user_repository import UserRepository
from app.schemas.users import UserRead

router = APIRouter()


@router.get("/", response_model=List[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Proxy para retrocompatibilidad. Ver /identity/users."""
    users = UserRepository.list_all(db)
    return [to_user_read(user) for user in users]
