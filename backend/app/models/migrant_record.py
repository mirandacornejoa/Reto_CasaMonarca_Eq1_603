from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.core.database import Base


class MigrantRecord(Base):
    __tablename__ = "migrant_records"

    id = Column(Integer, primary_key=True, index=True)
    folio = Column(String(30), unique=True, nullable=True, index=True)

    # ── Campos del formulario real de entrevista de ingreso ──
    attention_date = Column(Date, nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name_1 = Column(String(100), nullable=True)
    last_name_2 = Column(String(100), nullable=True, default="X")
    phone = Column(String(30), nullable=True)
    country_of_origin = Column(String(100), nullable=True)
    state_department = Column(String(100), nullable=True)
    civil_status = Column(String(30), nullable=True)
    birth_date = Column(Date, nullable=True)
    population_group = Column(String(60), nullable=True)

    # ── Campos legacy (compatibilidad con registros existentes) ──
    name_or_alias = Column(String(200), nullable=False)
    name_or_alias_enc = Column(Text, nullable=True)
    nationality = Column(String(100), nullable=True)
    language = Column(String(80), nullable=True)
    age_range = Column(String(30), nullable=True)
    gender = Column(String(50), nullable=True)
    contact_info = Column(String(255), nullable=True)
    contact_info_enc = Column(Text, nullable=True)
    needs = Column(Text, nullable=True)  # JSON array of needs
    registration_date = Column(DateTime, nullable=False, server_default=func.now())
    observations = Column(Text, nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    status = Column(String(30), nullable=False, default="REGISTRADO")
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)

    sha256_hash = Column(String(64), nullable=True)

    # ── Workflow operativo ──
    workflow_status = Column(String(20), nullable=False, default="pendiente")
    # pendiente → revisado → canalizado → cerrado
    assigned_operator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assigned_coordinator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    channeled_at = Column(DateTime, nullable=True)
    channel_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # ── Autoría ──
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ── Anonimización ARCO ──
    is_anonymized = Column(Boolean, nullable=False, default=False, server_default="0")
    anonymized_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

