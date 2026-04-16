from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.core.database import Base


class MigrantRecord(Base):
    __tablename__ = "migrant_records"

    id = Column(Integer, primary_key=True, index=True)
    folio = Column(String(30), unique=True, nullable=True, index=True)
    name_or_alias = Column(String(200), nullable=False)
    nationality = Column(String(100), nullable=True)
    language = Column(String(80), nullable=True)
    age_range = Column(String(30), nullable=True)
    gender = Column(String(50), nullable=True)
    contact_info = Column(String(255), nullable=True)
    needs = Column(Text, nullable=True)  # JSON array of needs
    registration_date = Column(DateTime, nullable=False, server_default=func.now())
    observations = Column(Text, nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    status = Column(String(30), nullable=False, default="REGISTRADO")
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)

    sha256_hash = Column(String(64), nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
