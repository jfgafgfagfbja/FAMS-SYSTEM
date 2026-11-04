"""Truy cap bang students."""
from collections.abc import Callable

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.db import models
from app.repositories.base import Page, paginate

ScopeFilter = Callable[[Query], Query]


def get(db: Session, student_id: int) -> models.Student | None:
    return db.get(models.Student, student_id)


def get_by_user(db: Session, user_id: int) -> models.Student | None:
    return db.query(models.Student).filter_by(user_id=user_id).first()


def get_by_code(db: Session, student_code: str) -> models.Student | None:
    return db.query(models.Student).filter_by(student_code=student_code).first()


def search(db: Session, *, scope: ScopeFilter, q: str | None, faculty_id: int | None,
           limit: int | None, offset: int) -> Page[models.Student]:
    """SV trong pham vi xem, tim theo MSSV hoac ho ten."""
    query = db.query(models.Student).join(models.User, models.Student.user_id == models.User.id)
    query = scope(query)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Student.student_code.ilike(like),
                                 models.User.full_name.ilike(like)))
    if faculty_id is not None:
        query = query.filter(models.Student.faculty_id == faculty_id)
    return paginate(query, models.Student.student_code, limit=limit, offset=offset)


def has_attendance_records(db: Session, student_id: int) -> bool:
    return db.query(models.AttendanceRecord).filter_by(student_id=student_id).first() is not None


def delete_parent_links(db: Session, student_id: int) -> None:
    db.query(models.ParentStudent).filter_by(student_id=student_id).delete()
