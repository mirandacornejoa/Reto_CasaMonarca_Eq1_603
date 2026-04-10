from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(190), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")
    is_active = Column(Boolean, nullable=False, default=False)

    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    access_level_id = Column(Integer, ForeignKey("access_levels.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    area = relationship("Area", back_populates="users")
    access_level = relationship("AccessLevel", back_populates="users")
    role = relationship("Role", back_populates="users")

    activation_tokens = relationship("ActivationToken", back_populates="user")
    credential = relationship("Credential", back_populates="user", uselist=False)
