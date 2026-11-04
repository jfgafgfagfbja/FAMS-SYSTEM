"""Truy cap bang staff (ho so can bo phong ban)."""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models
from app.repositories.base import Page, paginate


def get(db: Session, staff_id: int) -> models.Staff | None:
    return db.get(models.Staff, staff_id)


def get_by_user(db: Session, user_id: int) -> models.Staff | None:
    return db.query(models.Staff).filter_by(user_id=user_id).first()


def search(db: Session, *, q: str | None, unit_id: int | None, limit: int | None,
           offset: int) -> Page[models.Staff]:
    query = db.query(models.Staff).join(models.User, models.Staff.user_id == models.User.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.User.full_name.ilike(like),
                                 models.User.email.ilike(like)))
    if unit_id is not None:
        query = query.filter(models.Staff.unit_id == unit_id)
    return paginate(query, models.User.full_name, limit=limit, offset=offset)
