from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    matricula = Column(String(20), unique=True, nullable=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(190), unique=True, nullable=False, index=True)

    status = Column(String(20), nullable=False, default="PENDING")
    is_active = Column(Boolean, nullable=False, default=False)

    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    access_level_id = Column(Integer, ForeignKey("access_levels.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Subtipo de usuario (solo nivel 4): becario, voluntario, servicio_social, recepcion
    user_subtype = Column(String(30), nullable=True)
    # Área del coordinador (solo nivel 2): administracion, legal, psicosocial, humanitario, comunicacion
    coordinator_area = Column(String(30), nullable=True)
    # Asignación jerárquica: usuario→operativo, operativo→coordinador
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    area = relationship("Area", back_populates="users")
    access_level = relationship("AccessLevel", back_populates="users")
    role = relationship("Role", back_populates="users")

    # Relación jerárquica (self-referential)
    assigned_to = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[assigned_to_id],
    )
    subordinates = relationship(
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_to",
    )

    activation_tokens = relationship("ActivationToken", back_populates="user")
    otp_tokens = relationship("OtpToken", back_populates="user")
    credential = relationship("Credential", back_populates="user", uselist=False)
    certificates = relationship(
        "Certificate",
        back_populates="user",
        foreign_keys="Certificate.user_id",
        order_by="Certificate.created_at.desc()",
    )

    @property
    def active_certificate(self):
        """Returns the most recent VALID certificate, or None."""
        for cert in self.certificates:
            if cert.status == "VALID":
                return cert
        return None

    @property
    def latest_certificate(self):
        """Returns the most recent certificate regardless of status."""
        return self.certificates[0] if self.certificates else None
