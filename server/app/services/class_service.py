"""Nghiep vu lop hoc phan va ghi danh.

Pham vi: admin/P.DT moi lop; Van phong Khoa chi lop thuoc Khoa minh (core/authz.py); xem lop
theo pham vi xem (Khoa: lop Khoa quan ly, GV: lop minh day).
"""
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import (ensure_class_manage, ensure_class_view, ensure_enroll_schedule, faculty_for_new_class,
                            filter_classes, validate_faculty_id)
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.db import models
from app.repositories import class_repository, lecturer_repository, student_repository
from app.repositories.base import Page
from app.services.mappers import class_out, student_out


def get_or_404(db: Session, class_id: int) -> models.Class:
    clazz = class_repository.get(db, class_id)
    if not clazz:
        raise NotFoundError("Lop hoc phan khong ton tai")
    return clazz


def _validate_lecturer(db: Session, lecturer_id: int) -> None:
    if not lecturer_repository.get(db, lecturer_id):
        raise BadRequestError("Giang vien khong ton tai")


def _ensure_class_code_available(db: Session, class_code: str, exclude_id: int | None = None) -> None:
    existed = class_repository.get_by_code(db, class_code)
    if existed and existed.id != exclude_id:
        raise BadRequestError("Ma lop hoc phan da ton tai")


def create_class(db: Session, user: models.User, body: schemas.ClassCreate) -> schemas.ClassOut:
    _ensure_class_code_available(db, body.class_code)
    _validate_lecturer(db, body.lecturer_id)
    data = body.model_dump()
    data["faculty_id"] = faculty_for_new_class(user, db, data.get("faculty_id"))
    validate_faculty_id(db, data["faculty_id"])
    clazz = models.Class(**data)
    db.add(clazz)
    db.commit()
    db.refresh(clazz)
    return class_out(clazz, student_count=0)


def list_classes(db: Session, user: models.User, *, q: str | None, semester: str | None,
                 faculty_id: int | None, limit: int | None, offset: int) -> Page[schemas.ClassOut]:
    """Lop trong pham vi xem cua user, loc theo q (ma lop/ten mon), hoc ky, Khoa."""
    page = class_repository.search(
        db, scope=lambda query: filter_classes(query, user, db), q=q, semester=semester,
        faculty_id=faculty_id, limit=limit, offset=offset)
    counts = class_repository.student_counts(db, [c.id for c in page.items])
    return Page([class_out(c, student_count=counts.get(c.id, 0)) for c in page.items], page.total)


def get_class(db: Session, user: models.User, class_id: int) -> schemas.ClassOut:
    clazz = ensure_class_view(user, class_id, db)
    return class_out(clazz, student_count=class_repository.student_counts(db, [clazz.id]).get(clazz.id, 0))


def update_class(db: Session, user: models.User, class_id: int,
                 body: schemas.ClassUpdate) -> schemas.ClassOut:
    clazz = get_or_404(db, class_id)
    ensure_class_manage(user, clazz, db)
    data = body.model_dump(exclude_unset=True)
    if "faculty_id" in data:
        # Van phong Khoa khong chuyen lop sang Khoa khac.
        data["faculty_id"] = faculty_for_new_class(user, db, data["faculty_id"])
    if data.get("class_code"):
        _ensure_class_code_available(db, data["class_code"], exclude_id=class_id)
    if data.get("lecturer_id") is not None:
        _validate_lecturer(db, data["lecturer_id"])
    if "faculty_id" in data:
        validate_faculty_id(db, data["faculty_id"])
    for field, value in data.items():
        setattr(clazz, field, value)
    db.commit()
    db.refresh(clazz)
    return class_out(clazz)


def delete_class(db: Session, user: models.User, class_id: int) -> dict:
    clazz = get_or_404(db, class_id)
    ensure_class_manage(user, clazz, db)
    if class_repository.has_enrollments(db, class_id):
        raise ConflictError("Lop hoc phan da co sinh vien ghi danh, khong the xoa truc tiep")
    if class_repository.has_schedules(db, class_id):
        raise ConflictError("Lop hoc phan da co lich hoc, hay xoa lich hoc truoc")
    db.delete(clazz)
    db.commit()
    return {"ok": True}


def enroll_student(db: Session, user: models.User, class_id: int, student_id: int) -> dict:
    ensure_enroll_schedule(user)
    get_or_404(db, class_id)
    if not student_repository.get(db, student_id):
        raise NotFoundError("Sinh vien khong ton tai")
    if class_repository.is_enrolled(db, class_id, student_id):
        raise BadRequestError("Sinh vien da ghi danh lop nay")
    db.add(models.Enrollment(class_id=class_id, student_id=student_id))
    db.commit()
    return {"ok": True}


def unenroll_student(db: Session, user: models.User, class_id: int, student_id: int) -> dict:
    ensure_enroll_schedule(user)
    get_or_404(db, class_id)
    enrollment = class_repository.get_enrollment(db, class_id, student_id)
    if not enrollment:
        raise NotFoundError("Sinh vien chua ghi danh lop nay")
    db.delete(enrollment)
    db.commit()
    return {"ok": True}


def list_class_students(db: Session, user: models.User, class_id: int) -> list[schemas.StudentOut]:
    ensure_class_view(user, class_id, db)
    return [student_out(s) for s in class_repository.students_of_class(db, class_id)]
