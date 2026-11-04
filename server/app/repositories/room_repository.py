"""Truy cap bang rooms (phong hoc)."""
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import models


def get(db: Session, room_id: int) -> models.Room | None:
    return db.get(models.Room, room_id)


def code_taken(db: Session, code: str, exclude_id: int | None = None) -> bool:
    query = db.query(models.Room).filter(models.Room.code == code)
    if exclude_id is not None:
        query = query.filter(models.Room.id != exclude_id)
    return query.first() is not None


def search(db: Session, *, location_id: int | None, building: str | None, q: str | None,
           only_active: bool) -> list[models.Room]:
    query = db.query(models.Room)
    if location_id is not None:
        query = query.filter(models.Room.location_id == location_id)
    if building:
        query = query.filter(models.Room.building == building)
    if only_active:
        query = query.filter(models.Room.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(or_(models.Room.code.ilike(pattern), models.Room.name.ilike(pattern)))
    return query.order_by(models.Room.building, models.Room.floor, models.Room.code).all()


def schedule_counts(db: Session) -> dict[int, int]:
    """So lich hoc dang dung moi phong."""
    return dict(
        db.query(models.Schedule.room_id, func.count(models.Schedule.id))
        .filter(models.Schedule.room_id.isnot(None))
        .group_by(models.Schedule.room_id).all()
    )


def schedule_count(db: Session, room_id: int) -> int:
    return db.query(models.Schedule).filter_by(room_id=room_id).count()


def buildings(db: Session) -> list[str]:
    rows = (db.query(models.Room.building).filter(models.Room.building.isnot(None))
            .distinct().order_by(models.Room.building).all())
    return [r[0] for r in rows]
