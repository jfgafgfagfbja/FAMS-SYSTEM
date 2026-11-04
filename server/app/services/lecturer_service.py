"""Nghiep vu ho so giang vien."""
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import filter_lecturers, validate_faculty_id
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.db import models
from app.db.models import ROLE_LECTURER
from app.repositories import lecturer_repository
from app.repositories.base import Page
from app.services import account_service
from app.services.mappers import lecturer_out


def _get_or_404(db: Session, lecturer_id: int) -> models.Lecturer:
    lecturer = lecturer_repository.get(db, lecturer_id)
    if not lecturer:
        raise NotFoundError("Giang vien khong ton tai")
    return lecturer


def create_lecturer(db: Session, body: schemas.LecturerCreate) -> schemas.LecturerOut:
    account_service.ensure_email_available(db, body.email)
    if lecturer_repository.code_taken(db, body.lecturer_code):
        raise BadRequestError("Ma giang vien da ton tai")
    validate_faculty_id(db, body.faculty_id)

    user = account_service.new_user(db, email=body.email, password=body.password,
                                    role=ROLE_LECTURER, full_name=body.full_name)
    lecturer = models.Lecturer(user_id=user.id, lecturer_code=body.lecturer_code,
                               department=body.department, faculty_id=body.faculty_id)
    db.add(lecturer)
    db.commit()
    db.refresh(lecturer)
    return lecturer_out(lecturer)


def list_lecturers(db: Session, user: models.User, *, q: str | None, faculty_id: int | None,
                   limit: int | None, offset: int) -> Page[schemas.LecturerOut]:
    """q loc theo ma GV/ho ten; khong truyen limit thi tra ve toan bo (vd dropdown chon
    giang vien khi tao lop). Can bo Khoa chi thay GV thuoc Khoa minh."""
    page = lecturer_repository.search(
        db, scope=lambda query: filter_lecturers(query, user, db), q=q, faculty_id=faculty_id,
        limit=limit, offset=offset)
    return Page([lecturer_out(l) for l in page.items], page.total)


def update_lecturer(db: Session, lecturer_id: int, body: schemas.LecturerUpdate) -> schemas.LecturerOut:
    lecturer = _get_or_404(db, lecturer_id)
    data = body.model_dump(exclude_unset=True)
    if "faculty_id" in data:
        validate_faculty_id(db, data["faculty_id"])
    if "full_name" in data:
        lecturer.user.full_name = data.pop("full_name")
    for field, value in data.items():
        setattr(lecturer, field, value)
    db.commit()
    db.refresh(lecturer)
    return lecturer_out(lecturer)


def delete_lecturer(db: Session, lecturer_id: int) -> dict:
    lecturer = _get_or_404(db, lecturer_id)
    if lecturer_repository.teaches_any_class(db, lecturer_id):
        raise ConflictError("Giang vien dang phu trach lop hoc phan, khong the xoa truc tiep")
    user = lecturer.user
    account_service.ensure_no_attendance_edits(db, user.id)
    account_service.delete_profile_and_user(db, lecturer, user)
    db.commit()
    return {"ok": True}


def get_own_profile(db: Session, user: models.User) -> models.Lecturer:
    """Ho so cua chinh giang vien dang dang nhap."""
    if user.role != ROLE_LECTURER:
        raise ForbiddenError("Chi giang vien moi xem duoc lich day")
    lecturer = lecturer_repository.get_by_user(db, user.id)
    if not lecturer:
        raise NotFoundError("Khong tim thay ho so giang vien")
    return lecturer
