"""Truy cap bang attendance_sessions, attendance_records, attendance_audits."""
from collections.abc import Callable
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.db import models

ScopeFilter = Callable[[Query], Query]
ATTENDED_STATUSES = ("present", "late", "manual")


# ---------------- Phien ----------------

def get(db: Session, session_id: int) -> models.AttendanceSession | None:
    return db.get(models.AttendanceSession, session_id)


def get_for_schedule_on(db: Session, schedule_id: int, day: date) -> models.AttendanceSession | None:
    return (db.query(models.AttendanceSession)
            .filter_by(schedule_id=schedule_id, session_date=day).first())


def for_schedules_on(db: Session, schedule_ids: list[int], days: list[date]) -> list[models.AttendanceSession]:
    return (
        db.query(models.AttendanceSession)
        .filter(models.AttendanceSession.schedule_id.in_(schedule_ids),
                models.AttendanceSession.session_date.in_(days))
        .all()
    )


def open_sessions(db: Session) -> list[models.AttendanceSession]:
    return (db.query(models.AttendanceSession)
            .filter(models.AttendanceSession.status == "open").all())


def search(db: Session, *, scope: ScopeFilter, status: str | None, class_id: int | None,
           limit: int | None) -> list[models.AttendanceSession]:
    query = scope(db.query(models.AttendanceSession).join(models.Schedule).join(models.Class))
    if status:
        query = query.filter(models.AttendanceSession.status == status)
    if class_id is not None:
        query = query.filter(models.Class.id == class_id)
    query = query.order_by(models.AttendanceSession.session_date.desc(),
                           models.AttendanceSession.opened_at.desc())
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def closed_of_class(db: Session, class_id: int) -> list[models.AttendanceSession]:
    """Phien da dong cua lop, theo ngay tang dan."""
    return (
        db.query(models.AttendanceSession)
        .join(models.Schedule)
        .filter(models.Schedule.class_id == class_id,
                models.AttendanceSession.status == "closed")
        .order_by(models.AttendanceSession.session_date)
        .all()
    )


# ---------------- Ban ghi diem danh ----------------

def get_record(db: Session, record_id: int) -> models.AttendanceRecord | None:
    return db.get(models.AttendanceRecord, record_id)


def get_record_for(db: Session, session_id: int, student_id: int) -> models.AttendanceRecord | None:
    return (db.query(models.AttendanceRecord)
            .filter_by(session_id=session_id, student_id=student_id).first())


def records_of_session(db: Session, session_id: int) -> list[models.AttendanceRecord]:
    return db.query(models.AttendanceRecord).filter_by(session_id=session_id).all()


def records_of_student_in(db: Session, student_id: int,
                          session_ids: list[int]) -> list[models.AttendanceRecord]:
    return (
        db.query(models.AttendanceRecord)
        .filter(models.AttendanceRecord.session_id.in_(session_ids),
                models.AttendanceRecord.student_id == student_id)
        .all()
    )


def attended_counts(db: Session, session_ids: list[int]) -> dict[int, int]:
    """So SV co mat (present/late/manual) cua tung phien."""
    rows = (
        db.query(models.AttendanceRecord.session_id, func.count())
        .filter(models.AttendanceRecord.session_id.in_(session_ids),
                models.AttendanceRecord.status.in_(ATTENDED_STATUSES))
        .group_by(models.AttendanceRecord.session_id)
        .all()
    )
    return dict(rows)


def audits_of_record(db: Session, record_id: int) -> list[models.AttendanceAudit]:
    return (
        db.query(models.AttendanceAudit)
        .filter_by(record_id=record_id)
        .order_by(models.AttendanceAudit.changed_at.desc())
        .all()
    )
