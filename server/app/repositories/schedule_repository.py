"""Truy cap bang schedules (lich hoc trong tuan cua lop)."""
from collections.abc import Callable
from datetime import time

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.db import models
from app.repositories.base import Page, paginate

ScopeFilter = Callable[[Query], Query]


def get(db: Session, schedule_id: int) -> models.Schedule | None:
    return db.get(models.Schedule, schedule_id)


def of_class(db: Session, class_id: int) -> list[models.Schedule]:
    return (db.query(models.Schedule).filter_by(class_id=class_id)
            .order_by(models.Schedule.weekday, models.Schedule.start_time).all())


def of_classes(db: Session, class_ids: list[int]) -> list[models.Schedule]:
    return db.query(models.Schedule).filter(models.Schedule.class_id.in_(class_ids)).all()


def of_lecturer_on_weekday(db: Session, lecturer_id: int, weekday: int) -> list[models.Schedule]:
    return (
        db.query(models.Schedule)
        .join(models.Class)
        .filter(models.Class.lecturer_id == lecturer_id, models.Schedule.weekday == weekday)
        .order_by(models.Schedule.start_time)
        .all()
    )


def search(db: Session, *, scope: ScopeFilter, q: str | None, limit: int | None,
           offset: int) -> Page[models.Schedule]:
    """Lich kem lop trong pham vi xem; q tim theo ma lop, ten mon, ten phong (o chu) va
    ma/ten phong trong danh muc."""
    query = scope(db.query(models.Schedule).join(models.Class))
    if q:
        like = f"%{q}%"
        query = query.outerjoin(models.Room, models.Schedule.room_id == models.Room.id).filter(
            or_(models.Class.class_code.ilike(like),
                models.Class.subject_name.ilike(like),
                models.Schedule.room.ilike(like),
                models.Room.code.ilike(like),
                models.Room.name.ilike(like)))
    return paginate(query, models.Class.class_code, models.Schedule.weekday,
                    limit=limit, offset=offset)


def find_room_clash(db: Session, room_id: int, weekday: int, start: time, end: time,
                    exclude_id: int | None = None) -> models.Schedule | None:
    """Lich khac cung phong, cung thu, khung gio giao nhau (ket thuc = bat dau thi khong giao)."""
    query = (
        db.query(models.Schedule)
        .filter(models.Schedule.room_id == room_id,
                models.Schedule.weekday == weekday,
                models.Schedule.start_time < end,
                models.Schedule.end_time > start)
    )
    if exclude_id is not None:
        query = query.filter(models.Schedule.id != exclude_id)
    return query.first()


def has_sessions(db: Session, schedule_id: int) -> bool:
    return db.query(models.AttendanceSession).filter_by(schedule_id=schedule_id).first() is not None
