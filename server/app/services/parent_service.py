"""Nghiep vu phu huynh: tai khoan (admin/P.CTSV tao va lien ket thu cong, khong tu dang ky),
lien ket voi con, tuy chon thong bao, xem chuyen can cua con."""
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.db import models
from app.db.models import ROLE_PARENT
from app.repositories import parent_repository, student_repository
from app.repositories.base import Page
from app.services import account_service, email_service, report_service
from app.services.mappers import student_out


def _to_out(p: models.Parent) -> schemas.ParentOut:
    return schemas.ParentOut(
        id=p.id, full_name=p.user.full_name, email=p.user.email, phone=p.phone,
        child_count=len(p.children),
    )


def _child_to_out(s: models.Student) -> schemas.ParentChildOut:
    classes = [
        schemas.MeClassBrief(id=e.clazz.id, class_code=e.clazz.class_code,
                             subject_name=e.clazz.subject_name, semester=e.clazz.semester)
        for e in s.enrollments
    ]
    return student_out(s, out_cls=schemas.ParentChildOut, classes=classes)


def _get_or_404(db: Session, parent_id: int) -> models.Parent:
    parent = parent_repository.get(db, parent_id)
    if not parent:
        raise NotFoundError("Phu huynh khong ton tai")
    return parent


def _own_profile(db: Session, user: models.User) -> models.Parent:
    parent = parent_repository.get_by_user(db, user.id)
    if not parent:
        raise NotFoundError("Khong tim thay ho so phu huynh")
    return parent


def _ensure_own_child(db: Session, parent: models.Parent, student_id: int) -> models.Student:
    link = parent_repository.get_link(db, parent.id, student_id)
    if not link:
        raise ForbiddenError("Ban khong duoc lien ket voi sinh vien nay")
    return link.student


def _preferences_out(parent: models.Parent) -> schemas.ParentPreferencesOut:
    return schemas.ParentPreferencesOut(
        notify_email=parent.notify_email, notify_present=parent.notify_present,
        email_available=email_service.is_configured())


# ---- Admin/P.CTSV: quan ly tai khoan phu huynh ----

def create_parent(db: Session, body: schemas.ParentCreate) -> schemas.ParentOut:
    account_service.ensure_email_available(db, body.email)
    user = account_service.new_user(db, email=body.email, password=body.password,
                                    role=ROLE_PARENT, full_name=body.full_name)
    parent = models.Parent(user_id=user.id, phone=body.phone)
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return _to_out(parent)


def list_parents(db: Session, *, q: str | None, limit: int | None,
                 offset: int) -> Page[schemas.ParentOut]:
    page = parent_repository.search(db, q=q, limit=limit, offset=offset)
    return Page([_to_out(p) for p in page.items], page.total)


def update_parent(db: Session, parent_id: int, body: schemas.ParentUpdate) -> schemas.ParentOut:
    parent = _get_or_404(db, parent_id)
    data = body.model_dump(exclude_unset=True)
    if "full_name" in data:
        parent.user.full_name = data.pop("full_name")
    for field, value in data.items():
        setattr(parent, field, value)
    db.commit()
    db.refresh(parent)
    return _to_out(parent)


def delete_parent(db: Session, parent_id: int) -> dict:
    """Xoa tai khoan phu huynh kem cac lien ket voi con (khong xoa ho so SV)."""
    parent = _get_or_404(db, parent_id)
    account_service.delete_profile_and_user(db, parent, parent.user)  # cascade parent_students
    db.commit()
    return {"ok": True}


def list_children_of(db: Session, parent_id: int) -> list[schemas.StudentOut]:
    parent = _get_or_404(db, parent_id)
    return [student_out(link.student) for link in parent.children]


def link_child(db: Session, parent_id: int, body: schemas.ParentLinkChild) -> dict:
    """Lien ket phu huynh voi 1 SV bang MSSV (can bo khong phai tra cuu ID truoc)."""
    parent = _get_or_404(db, parent_id)
    student = student_repository.get_by_code(db, body.student_code)
    if not student:
        raise NotFoundError(f"Khong tim thay sinh vien voi MSSV {body.student_code}")
    if parent_repository.get_link(db, parent.id, student.id):
        raise BadRequestError("Da lien ket voi sinh vien nay roi")
    db.add(models.ParentStudent(parent_id=parent.id, student_id=student.id))
    db.commit()
    return {"ok": True}


def unlink_child(db: Session, parent_id: int, student_id: int) -> dict:
    link = parent_repository.get_link(db, parent_id, student_id)
    if not link:
        raise NotFoundError("Chua lien ket voi sinh vien nay")
    db.delete(link)
    db.commit()
    return {"ok": True}


# ---- Phu huynh: tuy chon thong bao, xem con em ----

def my_preferences(db: Session, user: models.User) -> schemas.ParentPreferencesOut:
    return _preferences_out(_own_profile(db, user))


def update_my_preferences(db: Session, user: models.User,
                          body: schemas.ParentPreferencesUpdate) -> schemas.ParentPreferencesOut:
    """Phu huynh tu bat/tat email thong bao, va tin bao khi con co mat."""
    parent = _own_profile(db, user)
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(parent, field, value)
    db.commit()
    return _preferences_out(parent)


def my_children(db: Session, user: models.User) -> list[schemas.ParentChildOut]:
    parent = _own_profile(db, user)
    return [_child_to_out(link.student) for link in parent.children]


def child_attendance(db: Session, user: models.User, student_id: int,
                     semester: str | None) -> list[schemas.MyClassAttendanceOut]:
    """Chuyen can cua con: dung lai chinh logic cua SV (report_service.student_attendance) de
    du lieu nhat quan - gom anh bang chung, gio, vi tri GPS tung buoi."""
    parent = _own_profile(db, user)
    student = _ensure_own_child(db, parent, student_id)
    return report_service.student_attendance(db, student, semester)
