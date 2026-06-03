from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    folio = Column(String(20), unique=True, nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(120), nullable=False)
    resource = Column(String(120), nullable=False)
    resource_id = Column(String(64), nullable=True)
    result = Column(String(20), nullable=False)
    detail = Column(Text, nullable=True)
    hash_related = Column(String(64), nullable=True)
    certificate_id = Column(Integer, ForeignKey("certificates.id"), nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
