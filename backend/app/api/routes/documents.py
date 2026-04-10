from fastapi import APIRouter, Depends

from app.core.deps import require_active_user

router = APIRouter()


@router.get("/placeholder")
def documents_placeholder(_: object = Depends(require_active_user)):
    return {
        "module": "documents",
        "status": "placeholder",
        "message": "La gestión documental completa se implementará en sprint 2.",
    }
