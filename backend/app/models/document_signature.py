from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class DocumentSignature(Base):
    """Evidencia de una firma documental realizada desde el navegador."""

    __tablename__ = "document_signatures"

    id = Column(Integer, primary_key=True, index=True)
    # El recurso firmado puede ser un document_id o un migrant_record_id
    resource_type = Column(String(40), nullable=False)   # "document" | "migrant_record"
    resource_id = Column(Integer, nullable=False, index=True)
    signer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    certificate_id = Column(Integer, ForeignKey("certificates.id"), nullable=False)
    # Hash SHA-256 del contenido que se firmó (lo que se pasó a sign())
    content_hash = Column(String(64), nullable=False)
    # Firma base64 producida por Web Crypto (ECDSA P-256 / RSA-PSS)
    signature_b64 = Column(Text, nullable=False)
    # Algoritmo usado, e.g. "ECDSA-P256-SHA256"
    algorithm = Column(String(40), nullable=False, default="ECDSA-P256-SHA256")
    signed_at = Column(DateTime, nullable=False, server_default=func.now())
    # Resultado de la última verificación: VALID | INVALID
    last_verification_result = Column(String(20), nullable=True)
    last_verified_at = Column(DateTime, nullable=True)

    signer = relationship("User", foreign_keys=[signer_user_id])
    certificate = relationship("Certificate", back_populates="document_signatures")
