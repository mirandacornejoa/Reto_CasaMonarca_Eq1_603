"""Servicio de plantillas de captura."""

import json
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.template import Template
from app.repositories.template_repository import TemplateRepository
from app.schemas.templates import TemplateCreate, TemplateUpdate


class TemplateService:
    @staticmethod
    def create_template(
        db: Session,
        payload: TemplateCreate,
        actor_user_id: int,
    ) -> Template:
        existing = TemplateRepository.get_by_name(db, payload.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una plantilla con ese nombre",
            )

        fields_json = json.dumps(
            [f.dict() for f in payload.fields],
            ensure_ascii=False,
        )

        template = Template(
            name=payload.name,
            description=payload.description,
            fields_json=fields_json,
            is_active=True,
            created_by_id=actor_user_id,
        )
        return TemplateRepository.create(db, template)

    @staticmethod
    def update_template(
        db: Session,
        template: Template,
        payload: TemplateUpdate,
    ) -> Template:
        if payload.name is not None:
            existing = TemplateRepository.get_by_name(db, payload.name)
            if existing and existing.id != template.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ya existe una plantilla con ese nombre",
                )
            template.name = payload.name

        if payload.description is not None:
            template.description = payload.description

        if payload.fields is not None:
            template.fields_json = json.dumps(
                [f.dict() for f in payload.fields],
                ensure_ascii=False,
            )

        return TemplateRepository.update(db, template)

    @staticmethod
    def toggle_status(db: Session, template: Template, is_active: bool) -> Template:
        template.is_active = is_active
        return TemplateRepository.update(db, template)

    @staticmethod
    def get_by_id(db: Session, template_id: int) -> Optional[Template]:
        return TemplateRepository.get_by_id(db, template_id)

    @staticmethod
    def list_templates(db: Session, active_only: bool = False) -> List[Template]:
        return TemplateRepository.list_all(db, active_only=active_only)
