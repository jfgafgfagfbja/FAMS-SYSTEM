"""Nghiep vu don vi (Khoa, P. Dao tao, P. CTSV, Ban nganh)."""
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.db import models
from app.repositories import unit_repository


def get_or_404(db: Session, unit_id: int) -> models.Unit:
    unit = unit_repository.get(db, unit_id)
    if not unit:
        raise NotFoundError("Don vi khong ton tai")
    return unit


def _ensure_code_available(db: Session, code: str, exclude_id: int | None = None) -> None:
    existed = unit_repository.get_by_code(db, code)
    if existed and existed.id != exclude_id:
        raise BadRequestError("Ma don vi da ton tai")


def list_units(db: Session, unit_type: str | None) -> list[models.Unit]:
    return unit_repository.list_units(db, unit_type)


def create_unit(db: Session, body: schemas.UnitCreate) -> models.Unit:
    _ensure_code_available(db, body.code)
    unit = models.Unit(**body.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def update_unit(db: Session, unit_id: int, body: schemas.UnitUpdate) -> models.Unit:
    """Doi ma/ten don vi. Khong cho doi loai don vi - vai tro can bo suy ra tu loai,
    doi loai se lam lech quyen cua can bo dang thuoc don vi (schema khong co truong type)."""
    unit = get_or_404(db, unit_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("code"):
        _ensure_code_available(db, data["code"], exclude_id=unit_id)
    for field, value in data.items():
        setattr(unit, field, value)
    db.commit()
    db.refresh(unit)
    return unit


def delete_unit(db: Session, unit_id: int) -> dict:
    unit = get_or_404(db, unit_id)
    if unit_repository.is_in_use(db, unit_id):
        raise ConflictError("Don vi dang co can bo/SV/GV/lop hoc phan, khong the xoa")
    db.delete(unit)
    db.commit()
    return {"ok": True}
