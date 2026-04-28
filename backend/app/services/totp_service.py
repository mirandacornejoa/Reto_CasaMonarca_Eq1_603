"""
Servicio TOTP real compatible con Google Authenticator, NetIQ Auth, Authy, etc.
Usa pyotp (RFC 6238 / TOTP) + Fernet para almacenar el secreto cifrado.

Flujo esperado:
  1. totp_service.begin_enrollment(user) → provisioning_uri + qr_data_url + secret_plain
  2. Usuario escanea QR / ingresa secreto manual en su app
  3. totp_service.confirm_enrollment(db, user, code) → True/False
  4. En login: totp_service.verify(user, code) → True/False
"""

import base64
import io
from datetime import datetime, timezone
from typing import Optional, Tuple

import pyotp
import qrcode
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.field_encryption_service import FieldEncryptionService


class TOTPService:
    ISSUER = "CasaMonarca"
    DIGITS = 6
    INTERVAL = 30  # segundos, estándar TOTP

    # ------------------------------------------------------------------
    #  Enrolamiento
    # ------------------------------------------------------------------
    @staticmethod
    def begin_enrollment(user: User) -> dict:
        """
        Genera un nuevo secreto TOTP para el usuario.
        Retorna {secret_plain, provisioning_uri, qr_data_url}.

        El secreto NO se persiste aquí — se persiste sólo cuando el usuario
        confirma el enrolamiento con un código válido.
        El frontend debe guardar secret_plain temporalmente para la confirmación.
        """
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, digits=TOTPService.DIGITS, interval=TOTPService.INTERVAL)
        provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name=TOTPService.ISSUER)

        # Generar QR como data URL (PNG en base64)
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        qr_data_url = f"data:image/png;base64,{qr_b64}"

        return {
            "secret_plain": secret,
            "provisioning_uri": provisioning_uri,
            "qr_data_url": qr_data_url,
        }

    @staticmethod
    def confirm_enrollment(db: Session, user: User, secret_plain: str, code: str) -> bool:
        """
        Verifica que el código TOTP sea válido para el secreto dado.
        Si es válido, persiste el secreto cifrado en la credencial del usuario.
        Retorna True si enrolamiento exitoso, False si código incorrecto.
        """
        totp = pyotp.TOTP(secret_plain, digits=TOTPService.DIGITS, interval=TOTPService.INTERVAL)
        # valid_window=1 acepta código del intervalo anterior y siguiente (±30s)
        if not totp.verify(code, valid_window=1):
            return False

        cred = user.credential
        if not cred:
            return False

        cred.totp_secret_enc = FieldEncryptionService.encrypt(secret_plain)
        cred.totp_enrolled = True
        cred.totp_enrolled_at = datetime.now(timezone.utc)
        db.add(cred)
        db.commit()
        return True

    # ------------------------------------------------------------------
    #  Verificación en login
    # ------------------------------------------------------------------
    @staticmethod
    def verify(user: User, code: str) -> bool:
        """
        Verifica un código TOTP para un usuario enrolado.
        Retorna True si válido, False si inválido o no enrolado.
        """
        cred = user.credential
        if not cred or not cred.totp_enrolled or not cred.totp_secret_enc:
            return False

        secret = FieldEncryptionService.decrypt(cred.totp_secret_enc)
        totp = pyotp.TOTP(secret, digits=TOTPService.DIGITS, interval=TOTPService.INTERVAL)
        return totp.verify(code, valid_window=1)

    # ------------------------------------------------------------------
    #  Revocación (admin)
    # ------------------------------------------------------------------
    @staticmethod
    def revoke_totp(db: Session, user: User) -> None:
        """Revoca/resetea el TOTP del usuario (admin o pérdida de dispositivo)."""
        cred = user.credential
        if not cred:
            return
        cred.totp_secret_enc = None
        cred.totp_enrolled = False
        cred.totp_enrolled_at = None
        db.add(cred)
        db.commit()

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def is_enrolled(user: User) -> bool:
        cred = user.credential
        return bool(cred and cred.totp_enrolled and cred.totp_secret_enc)
