"""Hop thu thong bao cua nguoi dang dang nhap (hien dung cho phu huynh - noi dung do
services/parent_notify.py sinh ra). Moi nguoi chi thay va chi danh dau duoc thong bao cua minh."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db import models
from app.repositories import notification_repository


def list_notifications(db: Session, user: models.User, *, unread_only: bool,
                       limit: int) -> list[models.Notification]:
    return notification_repository.list_for_user(db, user.id, unread_only=unread_only, limit=limit)


def unread_count(db: Session, user: models.User) -> dict:
    return {"count": notification_repository.count_unread(db, user.id)}


def mark_all_read(db: Session, user: models.User) -> dict:
    updated = notification_repository.mark_all_read(db, user.id, datetime.now())
    db.commit()
    return {"updated": updated}


def mark_read(db: Session, user: models.User, notification_id: int) -> models.Notification:
    item = notification_repository.get_for_user(db, user.id, notification_id)
    if not item:
        raise NotFoundError("Thong bao khong ton tai")
    if item.read_at is None:
        item.read_at = datetime.now()
        db.commit()
        db.refresh(item)
    return item
