from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    serial_number = Column(String(120), nullable=False, unique=True)
    # IDENTITY = certificado interno de identidad (original)
    # SIGNING   = certificado de firma documental (clave generada en navegador)
    cert_type = Column(String(20), nullable=False, default="IDENTITY")
    status = Column(String(40), nullable=False, default="VALID")
    fingerprint = Column(String(64), nullable=False)
    cert_data = Column(Text, nullable=False)
    issued_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    issued_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="certificates", foreign_keys=[user_id])
    document_signatures = relationship("DocumentSignature", back_populates="certificate")
