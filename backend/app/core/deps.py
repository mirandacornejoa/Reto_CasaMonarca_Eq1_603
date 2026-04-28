from datetime import datetime, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.services.permission_service import PermissionService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
        stage = payload.get("stage")
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    # Rechazar tokens pre-2FA que intentan acceder a recursos protegidos
    if stage == "pre_2fa":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de pre-autenticación. Complete el segundo factor.",
        )

    if stage != "authenticated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de acceso inválido. Se requiere autenticación completa.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


def get_pre2fa_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """Acepta tokens pre_2fa — usado para enrolamiento TOTP durante primer login."""
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
        stage = payload.get("stage")
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    if stage not in ("pre_2fa", "authenticated"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de acceso inválido.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


def require_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active or current_user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    # Validar vigencia
    if current_user.expires_at:
        now = datetime.now(timezone.utc)
        exp = current_user.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta ha expirado. Contacte al administrador.",
            )

    return current_user


def require_admin(current_user: User = Depends(require_active_user)) -> User:
    if not PermissionService.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere nivel administrador",
        )
    return current_user


def require_level(max_level: int) -> Callable:
    """Dependency factory: permite acceso si access_level.code <= max_level."""
    def checker(current_user: User = Depends(require_active_user)) -> User:
        if not current_user.access_level or current_user.access_level.code > max_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere nivel de acceso {max_level} o superior",
            )
        return current_user
    return checker


# Shortcuts comunes
require_admin = require_level(1)
require_coordinator_or_above = require_level(2)
require_operator_or_above = require_level(3)


def require_permission(permission_code: str) -> Callable:
    def checker(current_user: User = Depends(require_active_user)) -> User:
        if not PermissionService.has_permission(current_user, permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {permission_code}",
            )
        return current_user

    return checker
