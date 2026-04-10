from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(120), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(255), nullable=True)

    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")
