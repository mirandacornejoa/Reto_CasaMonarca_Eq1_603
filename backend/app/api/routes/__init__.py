from fastapi import APIRouter

from app.api.routes import audit, auth, certificates, documents, identity, records, roles, templates, users, verification

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(identity.router, prefix="/identity", tags=["identity"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(certificates.router, prefix="/certificates", tags=["certificates"])
api_router.include_router(records.router, prefix="/records", tags=["records"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])
