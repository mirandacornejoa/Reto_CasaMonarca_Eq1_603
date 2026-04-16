from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.certificate import Certificate


class CertificateRepository:
    @staticmethod
    def create(db: Session, certificate: Certificate) -> Certificate:
        db.add(certificate)
        db.commit()
        db.refresh(certificate)
        return certificate

    @staticmethod
    def get_by_id(db: Session, cert_id: int) -> Optional[Certificate]:
        return db.query(Certificate).filter(Certificate.id == cert_id).first()

    @staticmethod
    def get_by_user_id(db: Session, user_id: int) -> Optional[Certificate]:
        return db.query(Certificate).filter(Certificate.user_id == user_id).first()

    @staticmethod
    def list_all(db: Session, limit: int = 200) -> List[Certificate]:
        return db.query(Certificate).order_by(Certificate.created_at.desc()).limit(limit).all()

    @staticmethod
    def update_status(db: Session, certificate: Certificate, new_status: str) -> Certificate:
        certificate.status = new_status
        db.add(certificate)
        db.commit()
        db.refresh(certificate)
        return certificate

    @staticmethod
    def get_by_serial(db: Session, serial_number: str) -> Optional[Certificate]:
        return db.query(Certificate).filter(Certificate.serial_number == serial_number).first()
