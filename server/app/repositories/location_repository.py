"""Truy cap bang locations (dia diem/khu vuc diem danh)."""
from sqlalchemy.orm import Session

from app.db import models


def get(db: Session, location_id: int) -> models.Location | None:
    return db.get(models.Location, location_id)


def get_by_code(db: Session, code: str) -> models.Location | None:
    return db.query(models.Location).filter_by(code=code).first()


def get_default(db: Session) -> models.Location | None:
    return db.query(models.Location).filter_by(is_default=True).first()


def list_all(db: Session) -> list[models.Location]:
    return (db.query(models.Location)
            .order_by(models.Location.is_default.desc(), models.Location.name).all())


def clear_other_defaults(db: Session, keep_id: int) -> None:
    (db.query(models.Location)
     .filter(models.Location.id != keep_id, models.Location.is_default.is_(True))
     .update({"is_default": False}))


def used_by_schedules(db: Session, location_id: int) -> bool:
    return db.query(models.Schedule).filter_by(location_id=location_id).first() is not None
