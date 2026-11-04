"""Truy cap bang audit_logs (chi doc - viec ghi do services/audit.py tu dong lam)."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models
from app.repositories.base import Page


def search(db: Session, *, faculty_scope: int | None, q: str | None, action: str | None,
           success: bool | None, date_from: date | None, date_to: date | None,
           limit: int, offset: int) -> Page[models.AuditLog]:
    """faculty_scope khac None: chi nhat ky gan voi Khoa do. Moi nhat truoc."""
    query = db.query(models.AuditLog)
    if faculty_scope is not None:
        query = query.filter(models.AuditLog.faculty_id == faculty_scope)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(models.AuditLog.actor_email.ilike(like),
                                 models.AuditLog.target_label.ilike(like),
                                 models.AuditLog.action.ilike(like)))
    if action:
        query = query.filter(models.AuditLog.action.startswith(action))
    if success is not None:
        query = query.filter(models.AuditLog.success.is_(success))
    if date_from:
        query = query.filter(models.AuditLog.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(
            models.AuditLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    total = query.count()
    items = query.order_by(models.AuditLog.id.desc()).offset(offset).limit(limit).all()
    return Page(items, total)
