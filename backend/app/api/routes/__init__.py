from fastapi import APIRouter

from app.api.routes import audit, auth, documents, identity, roles, users, verification

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(identity.router, prefix="/identity", tags=["identity"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])
