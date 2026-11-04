"""Nghiep vu dia diem diem danh (toa do + ban kinh doi chieu GPS). Toi da 1 dia diem mac dinh."""
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.db import models
from app.repositories import location_repository


def _get_or_404(db: Session, location_id: int) -> models.Location:
    location = location_repository.get(db, location_id)
    if not location:
        raise NotFoundError("Dia diem khong ton tai")
    return location


def _ensure_code_available(db: Session, code: str, exclude_id: int | None = None) -> None:
    existed = location_repository.get_by_code(db, code)
    if existed and existed.id != exclude_id:
        raise BadRequestError("Ma dia diem da ton tai")


def list_locations(db: Session) -> list[models.Location]:
    return location_repository.list_all(db)


def create_location(db: Session, body: schemas.LocationCreate) -> models.Location:
    _ensure_code_available(db, body.code)
    location = models.Location(**body.model_dump())
    db.add(location)
    db.flush()
    if location.is_default:
        location_repository.clear_other_defaults(db, location.id)
    db.commit()
    db.refresh(location)
    return location


def update_location(db: Session, location_id: int, body: schemas.LocationUpdate) -> models.Location:
    location = _get_or_404(db, location_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("code"):
        _ensure_code_available(db, data["code"], exclude_id=location_id)
    for field, value in data.items():
        if value is not None:
            setattr(location, field, value)
    if location.is_default:
        location_repository.clear_other_defaults(db, location.id)
    db.commit()
    db.refresh(location)
    return location


def delete_location(db: Session, location_id: int) -> dict:
    location = _get_or_404(db, location_id)
    if location_repository.used_by_schedules(db, location_id):
        raise ConflictError(
            "Dia diem dang duoc gan cho lich hoc, hay doi lich hoc sang dia diem khac truoc")
    db.delete(location)
    db.commit()
    return {"ok": True}
