from fastapi import APIRouter

from app.api.routes import arco_requests, audit, auth, certificates, dashboard, deletion_requests, documents, identity, records, roles, signatures, users, verification

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(identity.router, prefix="/identity", tags=["identity"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(certificates.router, prefix="/certificates", tags=["certificates"])
api_router.include_router(records.router, prefix="/records", tags=["records"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(deletion_requests.router, prefix="/deletion-requests", tags=["deletion-requests"])
api_router.include_router(arco_requests.router, prefix="/arco-requests", tags=["arco"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])
api_router.include_router(signatures.router, prefix="/signatures", tags=["signatures"])
