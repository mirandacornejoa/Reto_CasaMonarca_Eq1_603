"""Endpoints de estado y verificación de firmas documentales."""

import base64
import json
from datetime import datetime, timezone
from typing import Optional

from cryptography import x509 as crypto_x509
from cryptography.exceptions import InvalidSignature as CryptoInvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.x509.oid import NameOID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_active_user
from app.models.certificate import Certificate
from app.models.document_signature import DocumentSignature
from app.models.user import User
from app.services.signing_service import SigningService


class VerifyCertPayload(BaseModel):
    cert_pem: str

router = APIRouter()


def _level(user: User) -> int:
    return user.access_level.code if user.access_level else 99


def _get_latest_sig(db: Session, resource_type: str, resource_id: int):
    return (
        db.query(DocumentSignature)
        .filter(
            DocumentSignature.resource_type == resource_type,
            DocumentSignature.resource_id == resource_id,
        )
        .order_by(DocumentSignature.signed_at.desc())
        .first()
    )


@router.get("/{resource_type}/{resource_id}")
def get_signature_status(
    resource_type: str,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Estado de firma para un recurso. Visible para niveles 1-3."""
    if _level(current_user) > 3:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    sig = _get_latest_sig(db, resource_type, resource_id)
    if not sig:
        return {"signed": False}

    signer = db.query(User).filter(User.id == sig.signer_user_id).first()
    cert = db.query(Certificate).filter(Certificate.id == sig.certificate_id).first()

    public_key_pem = None
    fingerprint = None
    certificate_serial = None
    cert_subject = None
    if cert:
        fingerprint = cert.fingerprint  # completo
        certificate_serial = cert.serial_number
        try:
            cert_data = json.loads(cert.cert_data)
            public_key_pem = cert_data.get("public_key_pem")
            subj = cert_data.get("subject", {})
            cert_subject = subj.get("full_name") or subj.get("email")
        except Exception:
            pass

    return {
        "signed": True,
        "signer_name": signer.full_name if signer else "Desconocido",
        "signer_matricula": getattr(signer, "matricula", None) if signer else None,
        "signed_at": sig.signed_at.isoformat() if sig.signed_at else None,
        "fingerprint": fingerprint,
        "public_key_pem": public_key_pem,
        "certificate_serial": certificate_serial,
        "cert_subject": cert_subject,
        "algorithm": sig.algorithm,
        "last_verification_result": sig.last_verification_result,
    }


@router.post("/{resource_type}/{resource_id}/verify")
def verify_stored_signature(
    resource_type: str,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Reverifica la firma almacenada usando la clave pública del certificado del firmante."""
    if _level(current_user) > 3:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    sig = _get_latest_sig(db, resource_type, resource_id)
    if not sig:
        return {"valid": False, "message": "No se encontró firma para este recurso"}

    cert = db.query(Certificate).filter(Certificate.id == sig.certificate_id).first()
    if not cert:
        return {"valid": False, "message": "Certificado del firmante no encontrado en el sistema"}

    cert_data = json.loads(cert.cert_data)
    public_key_pem = cert_data.get("public_key_pem")
    if not public_key_pem:
        return {"valid": False, "message": "Clave pública no disponible en el certificado"}

    is_valid = False
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        sig_bytes = base64.b64decode(sig.signature_b64)
        hash_bytes = bytes.fromhex(sig.content_hash)

        try:
            public_key.verify(sig_bytes, hash_bytes, ec.ECDSA(Prehashed(hashes.SHA256())))
            is_valid = True
        except CryptoInvalidSignature:
            converted = SigningService._p1363_to_der(sig_bytes)
            if converted:
                try:
                    public_key.verify(converted, hash_bytes, ec.ECDSA(Prehashed(hashes.SHA256())))
                    is_valid = True
                except CryptoInvalidSignature:
                    pass
    except Exception:
        pass

    result_str = "VALID" if is_valid else "INVALID"
    sig.last_verification_result = result_str
    sig.last_verified_at = datetime.now(timezone.utc)
    db.commit()

    signer = db.query(User).filter(User.id == sig.signer_user_id).first()

    public_key_pem = None
    cert_subject = None
    if cert:
        try:
            cert_data_parsed = json.loads(cert.cert_data)
            public_key_pem = cert_data_parsed.get("public_key_pem")
            subj = cert_data_parsed.get("subject", {})
            cert_subject = subj.get("full_name") or subj.get("email")
        except Exception:
            pass

    return {
        "valid": is_valid,
        "message": (
            "Firma válida — identidad del firmante verificada criptográficamente"
            if is_valid
            else "Firma inválida o datos alterados — no se puede confirmar la autoría"
        ),
        "signer_name": signer.full_name if signer else None,
        "signer_matricula": getattr(signer, "matricula", None) if signer else None,
        "cert_subject": cert_subject,
        "signed_at": sig.signed_at.isoformat() if sig.signed_at else None,
        "fingerprint": cert.fingerprint if cert else None,
        "public_key_pem": public_key_pem,
        "algorithm": sig.algorithm,
    }


@router.post("/{resource_type}/{resource_id}/verify-cert")
def verify_with_uploaded_cert(
    resource_type: str,
    resource_id: int,
    payload: VerifyCertPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Verifica la firma almacenada usando el certificado (.cer) que sube el usuario.
    El sistema comprueba que el certificado proporcionado corresponde a la firma
    y que pertenece al firmante registrado."""
    if _level(current_user) > 3:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    sig = _get_latest_sig(db, resource_type, resource_id)
    if not sig:
        return {"valid": False, "message": "No hay firma registrada para esta resolución."}

    # Parsear el .cer proporcionado por el usuario
    try:
        uploaded_cert = crypto_x509.load_pem_x509_certificate(payload.cert_pem.encode())
        provided_pub_key = uploaded_cert.public_key()
        try:
            cert_cn = uploaded_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        except Exception:
            cert_cn = None
    except Exception as exc:
        return {"valid": False, "message": f"El certificado proporcionado no es válido o no se puede leer: {exc}"}

    # Verificar la firma almacenada con la clave pública del .cer proporcionado
    sig_bytes = base64.b64decode(sig.signature_b64)
    hash_bytes = bytes.fromhex(sig.content_hash)
    is_valid = False
    try:
        try:
            provided_pub_key.verify(sig_bytes, hash_bytes, ec.ECDSA(Prehashed(hashes.SHA256())))
            is_valid = True
        except CryptoInvalidSignature:
            converted = SigningService._p1363_to_der(sig_bytes)
            if converted:
                try:
                    provided_pub_key.verify(converted, hash_bytes, ec.ECDSA(Prehashed(hashes.SHA256())))
                    is_valid = True
                except CryptoInvalidSignature:
                    pass
    except Exception:
        pass

    # Comprobar que el .cer pertenece al firmante registrado (comparar clave pública)
    matches_signer = False
    registered_cert = db.query(Certificate).filter(Certificate.id == sig.certificate_id).first()
    if registered_cert:
        try:
            cert_data_reg = json.loads(registered_cert.cert_data)
            registered_pub_pem = cert_data_reg.get("public_key_pem", "")
            provided_pub_pem = provided_pub_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()
            matches_signer = provided_pub_pem.strip() == registered_pub_pem.strip()
        except Exception:
            pass

    signer = db.query(User).filter(User.id == sig.signer_user_id).first()

    if is_valid and matches_signer:
        message = "Certificado y firma válidos — la resolución fue firmada por este certificado."
    elif is_valid and not matches_signer:
        message = "La firma es criptográficamente válida con este certificado, pero NO corresponde al firmante registrado en el sistema."
    else:
        message = "Firma inválida — el certificado proporcionado no corresponde a la firma de esta resolución."

    return {
        "valid": is_valid,
        "matches_signer": matches_signer,
        "cert_cn": cert_cn,
        "signer_name": signer.full_name if signer else None,
        "message": message,
    }
