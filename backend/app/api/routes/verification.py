from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
def verification_placeholder():
    return {
        "module": "verification",
        "status": "placeholder",
        "message": "La verificación pública de folio/hash será implementada en sprint 2.",
    }
