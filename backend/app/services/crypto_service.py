"""Servicio de criptografía interna — genera certificados RSA-2048 por usuario."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.models.user import User


class CryptoService:
    """Genera y gestiona certificados/objetos criptográficos internos."""

    @staticmethod
    def build_sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def issue_certificate(
        db: Session,
        user: User,
        expires_at: datetime,
        issued_by: Optional[int] = None,
    ) -> Certificate:
        """Emite un certificado interno al crear/provisionar un usuario.

        Genera un par de claves RSA-2048, serializa la clave pública como PEM,
        calcula un fingerprint SHA-256 del PEM, y crea el registro Certificate.
        """
        # Generar par de claves RSA-2048
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        # Serializar clave pública en PEM
        public_pem = public_key.public_bytes(
            encoding=Encoding.PEM,
            format=PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        # Construir datos del certificado
        serial_number = uuid4().hex
        issued_at = datetime.now(timezone.utc)

        cert_payload = {
            "serial_number": serial_number,
            "subject": {
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
            },
            "issuer": "CasaMonarca-IdentitySystem",
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "public_key_pem": public_pem,
        }

        cert_data_str = json.dumps(cert_payload, sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256(cert_data_str.encode("utf-8")).hexdigest()

        certificate = Certificate(
            user_id=user.id,
            serial_number=serial_number,
            status="VALID",
            fingerprint=fingerprint,
            cert_data=cert_data_str,
            issued_at=issued_at,
            expires_at=expires_at,
            issued_by=issued_by,
        )
        db.add(certificate)
        db.flush()
        return certificate

    @staticmethod
    def revoke_certificate(db: Session, certificate: Certificate) -> Certificate:
        """Revoca un certificado (cambia status a REVOKED)."""
        certificate.status = "REVOKED"
        db.add(certificate)
        db.flush()
        return certificate

    @staticmethod
    def reissue_certificate(
        db: Session,
        user: User,
        expires_at: datetime,
        issued_by: Optional[int] = None,
    ) -> Certificate:
        """Revoca certificados existentes VALID y emite uno nuevo."""
        for cert in user.certificates:
            if cert.status == "VALID":
                cert.status = "REVOKED"
                db.add(cert)
        db.flush()
        return CryptoService.issue_certificate(db, user, expires_at, issued_by=issued_by)

    @staticmethod
    def check_validity(certificate: Optional[Certificate]) -> tuple:
        """Verifica validez de un certificado. Retorna (is_valid, message)."""
        if certificate is None:
            return False, "No existe certificado emitido"

        if certificate.status == "REVOKED":
            return False, "Certificado revocado"

        now = datetime.now(timezone.utc)
        expires = certificate.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if now > expires:
            return False, "Certificado expirado"

        if certificate.status != "VALID":
            return False, f"Estado del certificado: {certificate.status}"

        return True, "Certificado válido"

    @staticmethod
    def compute_record_hash(data: dict) -> str:
        """Calcula hash SHA-256 de un diccionario de datos (registro de migrante)."""
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
