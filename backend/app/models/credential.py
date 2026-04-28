from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    identity_provider = Column(String(80), nullable=False, default="local")
    username = Column(String(190), nullable=False)
    password_hash = Column(String(255), nullable=True)
    password_updated_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)

    # TOTP — secreto cifrado con Fernet (clave FIELD_ENCRYPTION_KEY del .env)
    totp_secret_enc = Column(String(512), nullable=True)
    totp_enrolled = Column(Boolean, nullable=False, default=False)
    totp_enrolled_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="credential")
