import os
import warnings
from functools import lru_cache
from typing import List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_csv(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    def __init__(self) -> None:
        self.APP_NAME: str = os.getenv("APP_NAME", "Identity Access Demo")
        self.API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")

        _insecure_secrets = {"change-this-secret", "change-this-secret-in-production", "secret", ""}
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret")
        if self.SECRET_KEY in _insecure_secrets:
            warnings.warn(
                "SECRET_KEY no ha sido configurado con un valor seguro. "
                "Genera una clave aleatoria y configúrala en .env antes de usar en producción.",
                stacklevel=2,
            )
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = _get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60)

        self.DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
        self.MYSQL_HOST: Optional[str] = os.getenv("MYSQL_HOST")
        self.MYSQL_PORT: int = _get_int("MYSQL_PORT", 3306)
        self.MYSQL_USER: Optional[str] = os.getenv("MYSQL_USER")
        self.MYSQL_PASSWORD: Optional[str] = os.getenv("MYSQL_PASSWORD")
        self.MYSQL_DB: Optional[str] = os.getenv("MYSQL_DB")
        self.SQLITE_PATH: str = os.getenv("SQLITE_PATH", "./app.db")

        self.AUTO_CREATE_TABLES: bool = _get_bool("AUTO_CREATE_TABLES", True)

        self.SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
        self.SMTP_PORT: int = _get_int("SMTP_PORT", 587)
        self.SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
        self.SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
        self.SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "no-reply@demo.org")
        self.SMTP_USE_TLS: bool = _get_bool("SMTP_USE_TLS", True)

        self.ACTIVATION_TOKEN_EXPIRE_HOURS: int = _get_int("ACTIVATION_TOKEN_EXPIRE_HOURS", 48)
        self.ACTIVATION_URL_BASE: str = os.getenv(
            "ACTIVATION_URL_BASE", "http://localhost:5173/activate"
        )

        self.OTP_EXPIRE_MINUTES: int = _get_int("OTP_EXPIRE_MINUTES", 10)
        self.PRE2FA_TOKEN_EXPIRE_MINUTES: int = _get_int("PRE2FA_TOKEN_EXPIRE_MINUTES", 10)

        # Cifrado de campos sensibles (Fernet key, generada con Fernet.generate_key())
        self.FIELD_ENCRYPTION_KEY: Optional[str] = os.getenv("FIELD_ENCRYPTION_KEY")

        # TOTP enrollment token expiry (minutos) — token HTTP para confirmar enrolamiento
        self.TOTP_ENROLL_TOKEN_EXPIRE_MINUTES: int = _get_int("TOTP_ENROLL_TOKEN_EXPIRE_MINUTES", 10)

        self.ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@demo.org")
        self.ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin2026Seguro!")
        self.ADMIN_FULL_NAME: str = os.getenv("ADMIN_FULL_NAME", "Administrador del Sistema")

        self.CORS_ORIGINS: List[str] = _get_csv(
            "CORS_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]
        )

    @property
    def smtp_configured(self) -> bool:
        """True only if all required SMTP settings are present."""
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)

    @property
    def resolved_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        if all([self.MYSQL_HOST, self.MYSQL_USER, self.MYSQL_PASSWORD, self.MYSQL_DB]):
            return (
                f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            )

        return f"sqlite:///{self.SQLITE_PATH}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
