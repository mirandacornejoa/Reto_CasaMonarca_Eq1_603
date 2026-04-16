"""Rutas de plantillas de captura — solo admin."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.schemas.templates import TemplateCreate, TemplateRead, TemplateStatusUpdate, TemplateUpdate
from app.services.audit_service import AuditService
from app.services.template_service import TemplateService

router = APIRouter()


@router.get("/", response_model=List[TemplateRead])
def list_templates(
    active_only: bool = False,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    return TemplateService.list_templates(db, active_only=active_only)


@router.post("/", response_model=TemplateRead, status_code=201)
def create_template(
    payload: TemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    template = TemplateService.create_template(db, payload, admin.id)

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="templates.create",
        resource="template",
        resource_id=str(template.id),
        result="SUCCESS",
        detail=f"Plantilla creada: {template.name}",
        request=request,
    )
    return template


@router.patch("/{template_id}", response_model=TemplateRead)
def update_template(
    template_id: int,
    payload: TemplateUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    template = TemplateService.get_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    template = TemplateService.update_template(db, template, payload)

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="templates.update",
        resource="template",
        resource_id=str(template.id),
        result="SUCCESS",
        detail=f"Plantilla actualizada: {template.name}",
        request=request,
    )
    return template


@router.patch("/{template_id}/status", response_model=TemplateRead)
def update_template_status(
    template_id: int,
    payload: TemplateStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    template = TemplateService.get_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    template = TemplateService.toggle_status(db, template, payload.is_active)

    AuditService.log(
        db=db,
        actor_user_id=admin.id,
        action="templates.toggle_status",
        resource="template",
        resource_id=str(template.id),
        result="SUCCESS",
        detail=f"Plantilla {'activada' if payload.is_active else 'desactivada'}: {template.name}",
        request=request,
    )
    return template
