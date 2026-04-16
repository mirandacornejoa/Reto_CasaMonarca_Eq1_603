from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.template import Template


class TemplateRepository:
    @staticmethod
    def create(db: Session, template: Template) -> Template:
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def get_by_id(db: Session, template_id: int) -> Optional[Template]:
        return db.query(Template).filter(Template.id == template_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Template]:
        return db.query(Template).filter(Template.name == name).first()

    @staticmethod
    def list_all(db: Session, active_only: bool = False) -> List[Template]:
        query = db.query(Template)
        if active_only:
            query = query.filter(Template.is_active.is_(True))
        return query.order_by(Template.created_at.desc()).all()

    @staticmethod
    def update(db: Session, template: Template) -> Template:
        db.add(template)
        db.commit()
        db.refresh(template)
        return template
