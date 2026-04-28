"""
Servicio de firma documental — Modelo SAT.

Genera material criptográfico en el backend:
  - Certificado X.509 autofirmado (.cer PEM) con la clave pública ECDSA P-256
  - Clave privada cifrada (.key) con contraseña del usuario (PBKDF2 + AES-256-GCM)

El backend NUNCA persiste la clave privada. Solo guarda el certificado público.

Flujo de firma:
  1. El usuario carga su .key + contraseña en el navegador
  2. El frontend descifra la clave privada en memoria → firma ECDSA P-256
  3. El backend verifica la firma con la clave pública del certificado registrado
  4. Se valida ownership, vigencia, y estado del certificado

Algoritmo fijo: ECDSA + P-256 + SHA-256 (compatible con WebCrypto SubtleCrypto)
"""

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import uuid4

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.x509.oid import NameOID
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.models.document_signature import DocumentSignature
from app.models.user import User


# Parámetros de cifrado — DEBEN coincidir con webCrypto.js
PBKDF2_ITERATIONS = 600_000
SALT_LENGTH = 16
IV_LENGTH = 12


class SigningService:
    CERT_YEARS_DEFAULT = 1

    # ------------------------------------------------------------------
    #  Generación de certificado de firma (modelo SAT)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_signing_certificate(
        db: Session,
        user: User,
        key_password: str,
        issued_by: Optional[int] = None,
        years: int = 1,
    ) -> Tuple[Certificate, str, str]:
        """
        Genera material criptográfico de firma para el usuario.

        Retorna (certificate_db, cer_pem, key_pem):
          - certificate_db: registro persistido en BD (solo material público)
          - cer_pem: certificado público X.509 PEM (para descarga como .cer)
          - key_pem: clave privada cifrada con contraseña (para descarga como .key)

        La clave privada se descarta de memoria tras cifrarse.
        """
        from datetime import timedelta

        # Revocar certificados SIGNING anteriores del usuario
        now = datetime.now(timezone.utc)
        for cert in user.certificates:
            if cert.cert_type == "SIGNING" and cert.status == "VALID":
                cert.status = "REVOKED"
                cert.revoked_at = now
                db.add(cert)

        # ── Generar par de claves ECDSA P-256 ──
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()

        # ── Construir certificado X.509 autofirmado ──
        serial_number = int(uuid4().hex, 16)
        issued_at = now
        expires_at = issued_at.replace(year=issued_at.year + years)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Casa Monarca"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Firma Documental"),
            x509.NameAttribute(NameOID.COMMON_NAME, user.full_name),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, user.email),
        ])

        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(public_key)
            .serial_number(serial_number)
            .not_valid_before(issued_at)
            .not_valid_after(expires_at)
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=False,
                    content_commitment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
        )

        x509_cert = cert_builder.sign(private_key, hashes.SHA256())

        # Serializar certificado público → PEM
        cer_pem = x509_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

        # Exportar clave pública como SPKI PEM (para almacenar en cert_data)
        public_key_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        # ── Cifrar clave privada con contraseña del usuario ──
        # Formato compatible con webCrypto.js: salt(16) + iv(12) + AES-GCM(ciphertext+tag)
        pkcs8_bytes = private_key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

        key_pem = SigningService._encrypt_private_key(pkcs8_bytes, key_password)

        # ── Descartar clave privada de memoria ──
        del private_key
        del pkcs8_bytes

        # ── Persistir solo material público ──
        serial_hex = format(serial_number, "x")
        cert_payload = {
            "serial_number": serial_hex,
            "cert_type": "SIGNING",
            "subject": {
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
            },
            "issuer": "CasaMonarca-SigningAuthority",
            "algorithm": "ECDSA-P256-SHA256",
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "public_key_pem": public_key_pem,
            "x509_certificate_pem": cer_pem,
        }
        cert_data_str = json.dumps(cert_payload, sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256(cert_data_str.encode()).hexdigest()

        certificate = Certificate(
            user_id=user.id,
            cert_type="SIGNING",
            serial_number=serial_hex,
            status="VALID",
            fingerprint=fingerprint,
            cert_data=cert_data_str,
            issued_at=issued_at,
            expires_at=expires_at,
            issued_by=issued_by,
        )
        db.add(certificate)
        db.flush()

        return certificate, cer_pem, key_pem

    # ------------------------------------------------------------------
    #  Verificación de firma
    # ------------------------------------------------------------------
    @staticmethod
    def verify_signature(
        db: Session,
        user: User,
        resource_type: str,
        resource_id: int,
        content_hash: str,
        signature_b64: str,
    ) -> Tuple[bool, str]:
        """
        Verifica una firma ECDSA P-256 enviada desde el navegador.

        content_hash: hex SHA-256 del contenido canónico firmado
        signature_b64: firma en base64 (DER o raw 64 bytes según WebCrypto)

        Retorna (is_valid, mensaje).
        """
        # Obtener certificado de firma activo
        signing_cert = None
        for cert in user.certificates:
            if cert.cert_type == "SIGNING" and cert.status == "VALID":
                signing_cert = cert
                break

        if not signing_cert:
            return False, "El usuario no tiene certificado de firma activo"

        # Validar vigencia
        now = datetime.now(timezone.utc)
        exp = signing_cert.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            return False, "El certificado de firma ha expirado"

        # Validar que no está revocado (doble check)
        if signing_cert.status == "REVOKED":
            return False, "El certificado de firma ha sido revocado"

        # Cargar clave pública desde cert_data
        cert_payload = json.loads(signing_cert.cert_data)
        public_key_pem = cert_payload["public_key_pem"]

        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
        except Exception as e:
            return False, f"Clave pública inválida en certificado: {e}"

        # Decodificar firma
        try:
            sig_bytes = base64.b64decode(signature_b64)
        except Exception:
            return False, "Firma base64 inválida"

        # Validar content_hash
        try:
            hash_bytes = bytes.fromhex(content_hash)
        except ValueError:
            return False, "content_hash debe ser hex SHA-256"

        # WebCrypto exporta firmas ECDSA en formato IEEE P1363 (64 bytes raw: r||s)
        # cryptography espera DER, así que convertimos si necesario
        try:
            if isinstance(public_key, ec.EllipticCurvePublicKey):
                # Intentar verificar como DER primero
                try:
                    public_key.verify(sig_bytes, hash_bytes, ec.ECDSA(Prehashed(hashes.SHA256())))
                    is_valid = True
                except InvalidSignature:
                    # Intentar convertir IEEE P1363 → DER
                    converted = SigningService._p1363_to_der(sig_bytes)
                    if converted:
                        try:
                            public_key.verify(converted, hash_bytes, ec.ECDSA(Prehashed(hashes.SHA256())))
                            is_valid = True
                        except InvalidSignature:
                            is_valid = False
                    else:
                        is_valid = False
            else:
                is_valid = False
        except Exception:
            is_valid = False

        # Registrar evidencia
        if is_valid:
            sig_record = DocumentSignature(
                resource_type=resource_type,
                resource_id=resource_id,
                signer_user_id=user.id,
                certificate_id=signing_cert.id,
                content_hash=content_hash,
                signature_b64=signature_b64,
                algorithm="ECDSA-P256-SHA256",
                signed_at=datetime.now(timezone.utc),
                last_verification_result="VALID",
                last_verified_at=datetime.now(timezone.utc),
            )
            db.add(sig_record)
            db.flush()
        else:
            # Actualizar último intento en registro existente si hay
            existing = (
                db.query(DocumentSignature)
                .filter(
                    DocumentSignature.resource_type == resource_type,
                    DocumentSignature.resource_id == resource_id,
                    DocumentSignature.signer_user_id == user.id,
                )
                .order_by(DocumentSignature.signed_at.desc())
                .first()
            )
            if existing:
                existing.last_verification_result = "INVALID"
                existing.last_verified_at = datetime.now(timezone.utc)
                db.add(existing)

        return is_valid, ("Firma verificada correctamente" if is_valid else "Firma inválida — el archivo no corresponde a este usuario o la firma es incorrecta")

    # ------------------------------------------------------------------
    #  Obtener certificado público del usuario (para re-descarga de .cer)
    # ------------------------------------------------------------------
    @staticmethod
    def get_user_certificate_pem(user: User) -> Optional[str]:
        """Retorna el certificado X.509 PEM del usuario si tiene uno VALID."""
        for cert in user.certificates:
            if cert.cert_type == "SIGNING" and cert.status == "VALID":
                cert_payload = json.loads(cert.cert_data)
                return cert_payload.get("x509_certificate_pem")
        return None

    # ------------------------------------------------------------------
    #  Revocación
    # ------------------------------------------------------------------
    @staticmethod
    def revoke_signing_certificate(db: Session, user: User, revoked_by: Optional[int] = None) -> None:
        now = datetime.now(timezone.utc)
        for cert in user.certificates:
            if cert.cert_type == "SIGNING" and cert.status == "VALID":
                cert.status = "REVOKED"
                cert.revoked_at = now
                db.add(cert)
        db.commit()

    # ------------------------------------------------------------------
    #  Cifrado de clave privada (compatible con webCrypto.js)
    # ------------------------------------------------------------------
    @staticmethod
    def _encrypt_private_key(pkcs8_bytes: bytes, password: str) -> str:
        """
        Cifra la clave privada PKCS8 con contraseña usando PBKDF2+AES-256-GCM.
        Formato idéntico al de webCrypto.js para que el frontend pueda descifrarla.

        Estructura binaria: salt(16) + iv(12) + ciphertext_with_tag
        Envuelto en PEM con headers CASA MONARCA ENCRYPTED KEY.
        """
        salt = os.urandom(SALT_LENGTH)
        iv = os.urandom(IV_LENGTH)

        # Derivar clave AES-256 con PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        aes_key = kdf.derive(password.encode("utf-8"))

        # Cifrar con AES-256-GCM
        aesgcm = AESGCM(aes_key)
        ciphertext = aesgcm.encrypt(iv, pkcs8_bytes, None)

        # Combinar: salt + iv + ciphertext (GCM tag va incluido en ciphertext)
        combined = salt + iv + ciphertext

        # Serializar como PEM
        b64 = base64.b64encode(combined).decode("ascii")
        lines = "\n".join([b64[i:i + 64] for i in range(0, len(b64), 64)])
        return f"-----BEGIN CASA MONARCA ENCRYPTED KEY-----\n{lines}\n-----END CASA MONARCA ENCRYPTED KEY-----"

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _p1363_to_der(sig: bytes) -> Optional[bytes]:
        """Convierte firma ECDSA P1363 (r||s, 64 bytes) a formato DER."""
        if len(sig) != 64:
            return None
        try:
            from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
            r = int.from_bytes(sig[:32], "big")
            s = int.from_bytes(sig[32:], "big")
            return encode_dss_signature(r, s)
        except Exception:
            return None
