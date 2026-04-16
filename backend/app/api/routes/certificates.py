"""Rutas de certificados/objetos criptográficos internos."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_active_user, require_admin
from app.repositories.certificate_repository import CertificateRepository
from app.schemas.certificates import CertificateRead, CertificateValidationResponse
from app.services.audit_service import AuditService
from app.services.crypto_service import CryptoService

router = APIRouter()


@router.get("/", response_model=List[CertificateRead])
def list_certificates(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Admin: listar todos los certificados emitidos."""
    certs = CertificateRepository.list_all(db)
    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="certificates.list",
        resource="certificate",
        result="SUCCESS",
        request=request,
    )
    return certs


@router.get("/validate/{cert_id}", response_model=CertificateValidationResponse)
def validate_certificate(
    cert_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Validar estado de un certificado por ID."""
    cert = CertificateRepository.get_by_id(db, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    is_valid, message = CryptoService.check_validity(cert)

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="certificates.validate",
        resource="certificate",
        resource_id=str(cert_id),
        result="SUCCESS",
        detail=message,
        certificate_id=cert.id,
        request=request,
    )

    return CertificateValidationResponse(
        serial_number=cert.serial_number,
        status=cert.status,
        is_valid=is_valid,
        issued_at=cert.issued_at,
        expires_at=cert.expires_at,
        message=message,
    )


@router.get("/{cert_id}", response_model=CertificateRead)
def get_certificate(
    cert_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Admin: detalle completo de un certificado."""
    cert = CertificateRepository.get_by_id(db, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    AuditService.log(
        db=db,
        actor_user_id=current_user.id,
        action="certificates.read",
        resource="certificate",
        resource_id=str(cert_id),
        result="SUCCESS",
        certificate_id=cert.id,
        request=request,
    )
    return cert
