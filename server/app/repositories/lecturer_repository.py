"""Truy cap bang lecturers."""
from collections.abc import Callable

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.db import models
from app.repositories.base import Page, paginate

ScopeFilter = Callable[[Query], Query]


def get(db: Session, lecturer_id: int) -> models.Lecturer | None:
    return db.get(models.Lecturer, lecturer_id)


def get_by_user(db: Session, user_id: int) -> models.Lecturer | None:
    return db.query(models.Lecturer).filter_by(user_id=user_id).first()


def code_taken(db: Session, lecturer_code: str) -> bool:
    return db.query(models.Lecturer).filter_by(lecturer_code=lecturer_code).first() is not None


def teaches_any_class(db: Session, lecturer_id: int) -> bool:
    return db.query(models.Class).filter_by(lecturer_id=lecturer_id).first() is not None


def search(db: Session, *, scope: ScopeFilter, q: str | None, faculty_id: int | None,
           limit: int | None, offset: int) -> Page[models.Lecturer]:
    query = db.query(models.Lecturer).join(models.User, models.Lecturer.user_id == models.User.id)
    query = scope(query)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Lecturer.lecturer_code.ilike(like),
                                 models.User.full_name.ilike(like)))
    if faculty_id is not None:
        query = query.filter(models.Lecturer.faculty_id == faculty_id)
    return paginate(query, models.Lecturer.lecturer_code, limit=limit, offset=offset)
