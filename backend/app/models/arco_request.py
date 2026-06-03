from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ArcoRequest(Base):
    """Solicitud de ejercicio de derechos ARCO (Acceso, Rectificación, Cancelación, Oposición).

    Flujo por tipo:
      ACCESS / OPPOSITION  : PENDING → IN_REVIEW → COMPLETED
      RECTIFICATION        : PENDING → IN_REVIEW → COMPLETED
      CANCELLATION         : PENDING → IN_REVIEW → ESCALATED → APPROVED / REJECTED
    """

    __tablename__ = "arco_requests"

    id = Column(Integer, primary_key=True, index=True)
    folio = Column(String(30), unique=True, nullable=True, index=True)

    # Tipo y estado
    request_type = Column(String(20), nullable=False)
    # ACCESS | RECTIFICATION | CANCELLATION | OPPOSITION
    status = Column(String(30), nullable=False, default="PENDING")
    # PENDING | IN_REVIEW | ESCALATED | COMPLETED | APPROVED | REJECTED

    # Vínculos con registros y usuarios
    record_id = Column(
        Integer,
        ForeignKey("migrant_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_coordinator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Contenido de la solicitud
    reason = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    # JSON con campos a corregir — solo usado en RECTIFICATION
    requested_changes_json = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime, nullable=True)

    # Relaciones (lazy="select" por defecto)
    record = relationship("MigrantRecord", foreign_keys=[record_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    assigned_coordinator = relationship("User", foreign_keys=[assigned_coordinator_id])
    assigned_admin = relationship("User", foreign_keys=[assigned_admin_id])
