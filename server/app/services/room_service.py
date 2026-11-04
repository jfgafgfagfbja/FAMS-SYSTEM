"""Nghiep vu danh muc phong hoc: nguon chon phong khi xep lich, va la mot lop cua viec doi
chieu vi tri khi sinh vien tu diem danh (phong -> khu vuc chua phong)."""
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import BadRequestError, NotFoundError
from app.db import models
from app.repositories import location_repository, room_repository
from app.services.mappers import room_out


def _get_or_404(db: Session, room_id: int) -> models.Room:
    room = room_repository.get(db, room_id)
    if not room:
        raise NotFoundError("Phong hoc khong ton tai")
    return room


def _ensure_code_available(db: Session, code: str, exclude_id: int | None = None) -> None:
    if room_repository.code_taken(db, code, exclude_id):
        raise BadRequestError(f"Ma phong '{code}' da ton tai")


def _ensure_location(db: Session, location_id: int) -> None:
    if not location_repository.get(db, location_id):
        raise BadRequestError("Khu vuc khong ton tai")


def list_rooms(db: Session, *, location_id: int | None, building: str | None, q: str | None,
               only_active: bool) -> list[schemas.RoomOut]:
    rooms = room_repository.search(db, location_id=location_id, building=building, q=q,
                                   only_active=only_active)
    counts = room_repository.schedule_counts(db)
    return [room_out(r, counts.get(r.id, 0)) for r in rooms]


def list_buildings(db: Session) -> list[str]:
    return room_repository.buildings(db)


def create_room(db: Session, body: schemas.RoomCreate) -> schemas.RoomOut:
    _ensure_code_available(db, body.code)
    _ensure_location(db, body.location_id)
    room = models.Room(**body.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room_out(room)


def update_room(db: Session, room_id: int, body: schemas.RoomUpdate) -> schemas.RoomOut:
    room = _get_or_404(db, room_id)
    data = body.model_dump(exclude_unset=True)
    if "code" in data:
        _ensure_code_available(db, data["code"], exclude_id=room_id)
    if "location_id" in data:
        _ensure_location(db, data["location_id"])
    # Toa do phai con du cap sau khi gop thay doi vao ban ghi hien tai.
    lat = data.get("latitude", room.latitude)
    lng = data.get("longitude", room.longitude)
    if (lat is None) != (lng is None):
        raise BadRequestError("Phai co ca vi do va kinh do, hoac bo trong ca hai")
    for field, value in data.items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return room_out(room)


def delete_room(db: Session, room_id: int) -> dict:
    room = _get_or_404(db, room_id)
    used = room_repository.schedule_count(db, room_id)
    if used:
        raise BadRequestError(
            f"Phong dang duoc {used} lich hoc su dung. Hay doi phong cho cac lich do, "
            "hoac danh dau phong ngung su dung thay vi xoa")
    db.delete(room)
    db.commit()
    return {"ok": True}
