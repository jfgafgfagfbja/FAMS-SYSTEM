"""Truy cap bang units (Khoa, phong, ban)."""
from sqlalchemy.orm import Session

from app.db import models


def get(db: Session, unit_id: int) -> models.Unit | None:
    return db.get(models.Unit, unit_id)


def get_by_code(db: Session, code: str) -> models.Unit | None:
    return db.query(models.Unit).filter_by(code=code).first()


def list_units(db: Session, unit_type: str | None = None) -> list[models.Unit]:
    query = db.query(models.Unit)
    if unit_type:
        query = query.filter(models.Unit.type == unit_type)
    return query.order_by(models.Unit.type, models.Unit.name).all()


def is_in_use(db: Session, unit_id: int) -> bool:
    """Con can bo, SV, GV hoac lop hoc phan gan voi don vi."""
    return bool(
        db.query(models.Staff).filter_by(unit_id=unit_id).first()
        or db.query(models.Student).filter_by(faculty_id=unit_id).first()
        or db.query(models.Lecturer).filter_by(faculty_id=unit_id).first()
        or db.query(models.Class).filter_by(faculty_id=unit_id).first()
    )
