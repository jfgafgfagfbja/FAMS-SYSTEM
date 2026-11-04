"""Truy cap bang parents va parent_students (lien ket phu huynh - sinh vien)."""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models
from app.repositories.base import Page, paginate


def get(db: Session, parent_id: int) -> models.Parent | None:
    return db.get(models.Parent, parent_id)


def get_by_user(db: Session, user_id: int) -> models.Parent | None:
    return db.query(models.Parent).filter_by(user_id=user_id).first()


def search(db: Session, *, q: str | None, limit: int | None, offset: int) -> Page[models.Parent]:
    query = db.query(models.Parent).join(models.User, models.Parent.user_id == models.User.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.User.full_name.ilike(like),
                                 models.User.email.ilike(like)))
    return paginate(query, models.User.full_name, limit=limit, offset=offset)


def get_link(db: Session, parent_id: int, student_id: int) -> models.ParentStudent | None:
    return (db.query(models.ParentStudent)
            .filter_by(parent_id=parent_id, student_id=student_id).first())


def links_of_student(db: Session, student_id: int) -> list[models.ParentStudent]:
    return db.query(models.ParentStudent).filter_by(student_id=student_id).all()
