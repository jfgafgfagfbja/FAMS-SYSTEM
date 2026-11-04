"""Truy van thong ke chuyen can. Moi thong ke CHI tinh phien da dong (ca tu so lan mau so)."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import models

CLOSED = "closed"


def count_closed_sessions(db: Session, class_id: int) -> int:
    return (
        db.query(func.count(models.AttendanceSession.id))
        .join(models.Schedule)
        .filter(models.Schedule.class_id == class_id,
                models.AttendanceSession.status == CLOSED)
        .scalar()
    ) or 0


def count_closed_sessions_of(db: Session, class_ids: list[int]) -> int:
    return (
        db.query(func.count(models.AttendanceSession.id))
        .join(models.Schedule)
        .filter(models.Schedule.class_id.in_(class_ids),
                models.AttendanceSession.status == CLOSED)
        .scalar()
    ) or 0


def status_counts_by_student(db: Session, class_id: int) -> list[tuple[int, str, int]]:
    """(student_id, status, so buoi) tren cac phien da dong cua lop."""
    return (
        db.query(models.AttendanceRecord.student_id,
                 models.AttendanceRecord.status,
                 func.count().label("cnt"))
        .join(models.AttendanceSession)
        .join(models.Schedule)
        .filter(models.Schedule.class_id == class_id,
                models.AttendanceSession.status == CLOSED)
        .group_by(models.AttendanceRecord.student_id,
                  models.AttendanceRecord.status)
        .all()
    )


def status_counts_of_student(db: Session, class_id: int, student_id: int) -> list[tuple[str, int]]:
    return (
        db.query(models.AttendanceRecord.status, func.count().label("cnt"))
        .join(models.AttendanceSession)
        .join(models.Schedule)
        .filter(models.Schedule.class_id == class_id,
                models.AttendanceSession.status == CLOSED,
                models.AttendanceRecord.student_id == student_id)
        .group_by(models.AttendanceRecord.status)
        .all()
    )


def status_counts_of_classes(db: Session, class_ids: list[int]) -> list[tuple[str, int]]:
    return (
        db.query(models.AttendanceRecord.status, func.count())
        .join(models.AttendanceSession)
        .join(models.Schedule)
        .filter(models.Schedule.class_id.in_(class_ids),
                models.AttendanceSession.status == CLOSED)
        .group_by(models.AttendanceRecord.status)
        .all()
    )


def closed_records_of_class(db: Session, class_id: int) -> list[models.AttendanceRecord]:
    return (
        db.query(models.AttendanceRecord)
        .join(models.AttendanceSession)
        .join(models.Schedule)
        .filter(models.Schedule.class_id == class_id,
                models.AttendanceSession.status == CLOSED)
        .all()
    )


def distinct_students_of(db: Session, class_ids: list[int]) -> int:
    return (
        db.query(func.count(func.distinct(models.Enrollment.student_id)))
        .filter(models.Enrollment.class_id.in_(class_ids))
        .scalar()
    ) or 0
