"""Truy cap bang classes (lop hoc phan) va enrollments (ghi danh)."""
from collections.abc import Callable

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from app.db import models
from app.repositories.base import Page, paginate

ScopeFilter = Callable[[Query], Query]


def get(db: Session, class_id: int) -> models.Class | None:
    return db.get(models.Class, class_id)


def get_by_code(db: Session, class_code: str) -> models.Class | None:
    return db.query(models.Class).filter_by(class_code=class_code).first()


def search(db: Session, *, scope: ScopeFilter, q: str | None, semester: str | None,
           faculty_id: int | None, limit: int | None, offset: int) -> Page[models.Class]:
    query = scope(db.query(models.Class))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Class.class_code.ilike(like),
                                 models.Class.subject_name.ilike(like)))
    if semester:
        query = query.filter(models.Class.semester == semester)
    if faculty_id is not None:
        query = query.filter(models.Class.faculty_id == faculty_id)
    return paginate(query, models.Class.class_code, limit=limit, offset=offset)


def list_in_scope(db: Session, scope: ScopeFilter) -> list[models.Class]:
    return scope(db.query(models.Class)).all()


def by_ids(db: Session, class_ids: list[int]) -> list[models.Class]:
    return db.query(models.Class).filter(models.Class.id.in_(class_ids)).all()


def of_lecturer(db: Session, lecturer_id: int) -> list[models.Class]:
    return db.query(models.Class).filter_by(lecturer_id=lecturer_id).all()


def student_counts(db: Session, class_ids: list[int]) -> dict[int, int]:
    """Si so tung lop."""
    if not class_ids:
        return {}
    rows = (
        db.query(models.Enrollment.class_id, func.count())
        .filter(models.Enrollment.class_id.in_(class_ids))
        .group_by(models.Enrollment.class_id)
        .all()
    )
    return dict(rows)


def has_enrollments(db: Session, class_id: int) -> bool:
    return db.query(models.Enrollment).filter_by(class_id=class_id).first() is not None


def has_schedules(db: Session, class_id: int) -> bool:
    return db.query(models.Schedule).filter_by(class_id=class_id).first() is not None


def get_enrollment(db: Session, class_id: int, student_id: int) -> models.Enrollment | None:
    return db.query(models.Enrollment).filter_by(class_id=class_id, student_id=student_id).first()


def is_enrolled(db: Session, class_id: int, student_id: int) -> bool:
    return get_enrollment(db, class_id, student_id) is not None


def enrolled_student_ids(db: Session, class_id: int) -> list[int]:
    return [sid for (sid,) in
            db.query(models.Enrollment.student_id).filter_by(class_id=class_id).all()]


def students_of_class(db: Session, class_id: int) -> list[models.Student]:
    return (
        db.query(models.Student)
        .join(models.Enrollment, models.Enrollment.student_id == models.Student.id)
        .filter(models.Enrollment.class_id == class_id)
        .order_by(models.Student.student_code)
        .all()
    )


def _in_faculty(db: Session, faculty_scope: int | None) -> Query:
    """faculty_scope None = toan truong; khac None = chi lop cua Khoa do."""
    query = db.query(models.Class)
    if faculty_scope is not None:
        query = query.filter(models.Class.faculty_id == faculty_scope)
    return query


def semesters(db: Session, faculty_scope: int | None) -> list[str]:
    """Cac hoc ky dang co lop, moi nhat truoc."""
    query = _in_faculty(db, faculty_scope).with_entities(models.Class.semester).distinct()
    return sorted({sem for (sem,) in query}, reverse=True)


def of_semester(db: Session, semester: str, faculty_scope: int | None) -> list[models.Class]:
    return _in_faculty(db, faculty_scope).filter(models.Class.semester == semester).all()
