"""Nghiep vu ho so sinh vien va dong y su dung du lieu khuon mat (PH4)."""
from sqlalchemy.orm import Session

from app import schemas
from app.core import consent as consent_policy
from app.core.authz import STUDENT_MANAGERS, ensure_student_view, filter_students, validate_faculty_id
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.db import models
from app.db.models import ROLE_STUDENT
from app.repositories import student_repository
from app.repositories.base import Page
from app.modules.m01_auth import account_service
from app.services.consent_service import record_consent, withdraw_consent
from app.services.mappers import student_out


def get_or_404(db: Session, student_id: int) -> models.Student:
    student = student_repository.get(db, student_id)
    if not student:
        raise NotFoundError("Sinh vien khong ton tai")
    return student


def create_student(db: Session, body: schemas.StudentCreate) -> schemas.StudentOut:
    account_service.ensure_email_available(db, body.email)
    if student_repository.get_by_code(db, body.student_code):
        raise BadRequestError("MSSV da ton tai")
    validate_faculty_id(db, body.faculty_id)

    user = account_service.new_user(db, email=body.email, password=body.password,
                                    role=ROLE_STUDENT, full_name=body.full_name)
    student = models.Student(user_id=user.id, student_code=body.student_code,
                             major=body.major, cohort=body.cohort, faculty_id=body.faculty_id)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student_out(student)


def list_students(db: Session, user: models.User, *, q: str | None, faculty_id: int | None,
                  limit: int | None, offset: int) -> Page[schemas.StudentOut]:
    """SV trong pham vi xem cua user (Khoa: SV thuoc Khoa, GV: SV lop minh day), loc theo q
    (MSSV hoac ho ten)/faculty_id. Khong truyen limit -> toan bo."""
    page = student_repository.search(
        db, scope=lambda query: filter_students(query, user, db), q=q, faculty_id=faculty_id,
        limit=limit, offset=offset)
    return Page([student_out(s) for s in page.items], page.total)


def consent_policy_text() -> schemas.ConsentPolicyOut:
    """Noi dung dong y su dung du lieu khuon mat dang hien hanh (co phien ban)."""
    return schemas.ConsentPolicyOut(
        version=consent_policy.CONSENT_VERSION, title=consent_policy.CONSENT_TITLE,
        items=consent_policy.consent_items(), checkbox=consent_policy.CONSENT_CHECKBOX)


def get_my_record(db: Session, user: models.User) -> schemas.StudentOut:
    if user.role != ROLE_STUDENT:
        raise ForbiddenError("Chi sinh vien moi co ho so nay")
    student = student_repository.get_by_user(db, user.id)
    if not student:
        raise NotFoundError("Khong tim thay ho so sinh vien")
    return student_out(student)


def get_student(db: Session, user: models.User, student_id: int) -> schemas.StudentOut:
    return student_out(ensure_student_view(user, student_id, db))


def update_student(db: Session, student_id: int, body: schemas.StudentUpdate) -> schemas.StudentOut:
    student = get_or_404(db, student_id)
    data = body.model_dump(exclude_unset=True)
    if "faculty_id" in data:
        validate_faculty_id(db, data["faculty_id"])
    if "full_name" in data:
        student.user.full_name = data.pop("full_name")
    for field, value in data.items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return student_out(student)


def delete_student(db: Session, student_id: int) -> dict:
    """Chi xoa SV chua co du lieu: da ghi danh/co khuon mat hoac co diem danh thi giu lai."""
    student = get_or_404(db, student_id)
    if student.enrollments or student.embeddings:
        raise ConflictError(
            "Sinh vien da co du lieu dang ky lop/khuon mat, khong the xoa truc tiep")
    if student_repository.has_attendance_records(db, student_id):
        raise ConflictError(
            "Sinh vien da co du lieu diem danh, khong the xoa (giu lai de doi chieu)")

    user = student.user
    student_repository.delete_parent_links(db, student_id)
    account_service.delete_profile_and_user(db, student, user)
    db.commit()
    return {"ok": True}


def give_consent(db: Session, user: models.User, student_id: int,
                 body: schemas.ConsentRequest) -> dict:
    """Ghi nhan dong y su dung du lieu khuon mat.

    - Chinh SV: method="self", sau khi doc noi dung trong app.
    - P.CTSV/admin: chi method="paper" - SV da ky ban giay, can bo nhap thay; ghi lai ten
      can bo da nhap. Can bo khong "dong y thay" SV khi khong co giay.
    Bat buoc gui dung phien ban noi dung dang hien hanh: dong y voi dung cai da doc.
    """
    student = get_or_404(db, student_id)
    is_self = user.role == ROLE_STUDENT and student.user_id == user.id
    if not is_self and user.role not in STUDENT_MANAGERS:
        raise ForbiddenError("Chi sinh vien hoac admin/P.CTSV moi xac nhan duoc dong y")
    if not body.agreed:
        raise BadRequestError("Can tick xac nhan dong y")
    if body.version != consent_policy.CONSENT_VERSION:
        raise ConflictError("Noi dung dong y da thay doi, vui long doc lai noi dung moi")
    expected = consent_policy.METHOD_SELF if is_self else consent_policy.METHOD_PAPER
    if body.method != expected:
        raise BadRequestError(
            "Sinh vien tu xac nhan trong ung dung" if is_self
            else "Can bo chi nhap dong y khi sinh vien da ky ban giay (method=paper)")
    record_consent(student, expected, user.email)
    db.commit()
    return {"ok": True, "consent_given": True, "version": student.consent_version,
            "method": student.consent_method}


def withdraw_student_consent(db: Session, user: models.User, student_id: int) -> dict:
    """Rut dong y: xoa ngay toan bo anh va vector khuon mat. SV tu rut, hoac P.CTSV/admin
    lam thay khi SV nop don."""
    student = get_or_404(db, student_id)
    is_self = user.role == ROLE_STUDENT and student.user_id == user.id
    if not is_self and user.role not in STUDENT_MANAGERS:
        raise ForbiddenError("Chi sinh vien hoac admin/P.CTSV moi rut duoc dong y")
    deleted = withdraw_consent(db, student)
    db.commit()
    return {"ok": True, "consent_given": False, "deleted": deleted}
