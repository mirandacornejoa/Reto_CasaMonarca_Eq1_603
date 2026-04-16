from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
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

    user = relationship("User", back_populates="credential")
