from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TwoFactorChallengeResponse(BaseModel):
    requires_2fa: bool = True
    session_token: str
    # "totp" = app autenticadora (único segundo factor soportado)
    two_fa_type: str = "totp"
    # True cuando el usuario aún no ha enrolado TOTP y debe hacerlo
    requires_totp_enrollment: bool = False
    demo_otp: Optional[str] = None


class Verify2FARequest(BaseModel):
    session_token: str
    otp_code: str = Field(min_length=6, max_length=6)


class PermissionRead(BaseModel):
    code: str
    name: str

    class Config:
        orm_mode = True


class MeResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    status: str
    is_active: bool
    area_id: Optional[int]
    area_name: Optional[str]
    access_level_code: int
    access_level_name: str
    role_id: int
    role_name: str
    permissions: List[PermissionRead]


class ActivateAccountRequest(BaseModel):
    token: str = Field(min_length=16)
    password: str = Field(min_length=12, max_length=128)


class DemoActivationResponse(BaseModel):
    full_name: str
    email: EmailStr
    activation_link: str


# ------------------------------------------------------------------ #
#  TOTP                                                                #
# ------------------------------------------------------------------ #

class TOTPEnrollBeginResponse(BaseModel):
    secret_plain: str
    provisioning_uri: str
    qr_data_url: str


class TOTPEnrollConfirmRequest(BaseModel):
    secret_plain: str = Field(min_length=16, max_length=64)
    totp_code: str = Field(min_length=6, max_length=6)


class TOTPStatusResponse(BaseModel):
    totp_enrolled: bool
    totp_enrolled_at: Optional[str] = None


# ------------------------------------------------------------------ #
#  Firma documental — Modelo SAT                                       #
# ------------------------------------------------------------------ #

class SigningCertEnrollRequest(BaseModel):
    """El usuario envía su contraseña para proteger la clave privada."""
    key_password: str = Field(min_length=8, max_length=128)
    years: int = Field(default=1, ge=1, le=5)


class SigningCertStatusResponse(BaseModel):
    has_signing_cert: bool
    cert_id: Optional[int] = None
    serial_number: Optional[str] = None
    status: Optional[str] = None
    issued_at: Optional[str] = None
    expires_at: Optional[str] = None
    fingerprint: Optional[str] = None


class SigningEnrollResponse(BaseModel):
    """Respuesta de enrolamiento con los archivos para descarga única."""
    certificate: SigningCertStatusResponse
    # Archivos en base64 para descarga desde el frontend
    cer_pem: str  # Certificado público X.509 PEM (.cer)
    key_pem: str  # Clave privada cifrada (.key)


class VerifySignatureRequest(BaseModel):
    resource_type: str = Field(min_length=1, max_length=40)
    resource_id: int
    content_hash: str = Field(min_length=64, max_length=64)
    signature_b64: str


class VerifySignatureResponse(BaseModel):
    is_valid: bool
    message: str
    signature_id: Optional[int] = None
