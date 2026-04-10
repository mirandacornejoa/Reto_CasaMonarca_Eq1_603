from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class AccessLevel(Base):
    __tablename__ = "access_levels"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(120), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    roles = relationship("Role", back_populates="access_level")
    users = relationship("User", back_populates="access_level")
