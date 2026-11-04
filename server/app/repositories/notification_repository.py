"""Truy cap bang notifications - luon gioi han theo nguoi nhan."""
from datetime import datetime

from sqlalchemy.orm import Query, Session

from app.db import models


def _of_user(db: Session, user_id: int) -> Query:
    return db.query(models.Notification).filter(models.Notification.user_id == user_id)


def list_for_user(db: Session, user_id: int, *, unread_only: bool,
                  limit: int) -> list[models.Notification]:
    query = _of_user(db, user_id)
    if unread_only:
        query = query.filter(models.Notification.read_at.is_(None))
    return query.order_by(models.Notification.id.desc()).limit(limit).all()


def count_unread(db: Session, user_id: int) -> int:
    return _of_user(db, user_id).filter(models.Notification.read_at.is_(None)).count()


def mark_all_read(db: Session, user_id: int, at: datetime) -> int:
    return (_of_user(db, user_id).filter(models.Notification.read_at.is_(None))
            .update({models.Notification.read_at: at}, synchronize_session=False))


def get_for_user(db: Session, user_id: int, notification_id: int) -> models.Notification | None:
    """Loc theo nguoi nhan ngay trong truy van: thong bao cua nguoi khac coi nhu khong ton tai."""
    return _of_user(db, user_id).filter(models.Notification.id == notification_id).first()
