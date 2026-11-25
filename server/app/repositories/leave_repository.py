"""Truy cap bang leave_requests (don xin phep vang)."""
from datetime import date

from sqlalchemy.orm import Query, Session

from app.db import models


def get(db: Session, leave_id: int) -> models.LeaveRequest | None:
    return db.get(models.LeaveRequest, leave_id)


def find(db: Session, student_id: int, schedule_id: int, absence_date: date) -> models.LeaveRequest | None:
    return db.query(models.LeaveRequest).filter_by(
        student_id=student_id, schedule_id=schedule_id, absence_date=absence_date).first()


def base_query(db: Session) -> Query:
    """Don kem lich, lop, SV - de loc theo pham vi (authz.filter_leave_requests)."""
    return (db.query(models.LeaveRequest)
            .join(models.Schedule, models.LeaveRequest.schedule_id == models.Schedule.id)
            .join(models.Class, models.Schedule.class_id == models.Class.id)
            .join(models.Student, models.LeaveRequest.student_id == models.Student.id))


def search(query: Query, *, status: str | None, class_id: int | None, limit: int) -> list[models.LeaveRequest]:
    if status:
        query = query.filter(models.LeaveRequest.status == status)
    if class_id is not None:
        query = query.filter(models.Schedule.class_id == class_id)
    return query.order_by(models.LeaveRequest.created_at.desc(), models.LeaveRequest.id.desc()).limit(limit).all()


def approved_student_ids(db: Session, schedule_id: int, absence_date: date) -> set[int]:
    """SV co don xin phep DA DUYET cho buoi (lich, ngay) - dong phien ghi excused thay vi absent."""
    rows = db.query(models.LeaveRequest.student_id).filter_by(
        schedule_id=schedule_id, absence_date=absence_date, status="approved").all()
    return {r[0] for r in rows}
