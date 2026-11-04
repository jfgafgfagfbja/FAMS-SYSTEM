"""Nghiep vu tai khoan can bo phong ban. Vai tro suy ra tu loai don vi."""
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import BadRequestError, NotFoundError
from app.db import models
from app.db.models import ROLE_BY_UNIT_TYPE, ROLE_FACULTY, ROLE_FACULTY_LEADER, UNIT_FACULTY
from app.repositories import staff_repository, unit_repository
from app.repositories.base import Page
from app.services import account_service
from app.services.mappers import staff_out


def _get_unit(db: Session, unit_id: int) -> models.Unit:
    unit = unit_repository.get(db, unit_id)
    if not unit:
        raise BadRequestError("Don vi khong ton tai")
    return unit


def _get_or_404(db: Session, staff_id: int) -> models.Staff:
    staff = staff_repository.get(db, staff_id)
    if not staff:
        raise NotFoundError("Can bo khong ton tai")
    return staff


def role_for(unit: models.Unit, faculty_leader: bool) -> str:
    """Vai tro cua can bo theo don vi. Don vi Khoa co hai vai tro: Lanh dao Khoa hoac Van
    phong Khoa; cac don vi khac chi co mot."""
    if unit.type == UNIT_FACULTY:
        return ROLE_FACULTY_LEADER if faculty_leader else ROLE_FACULTY
    if faculty_leader:
        raise BadRequestError("Chi don vi loai Khoa moi co Lanh dao Khoa")
    return ROLE_BY_UNIT_TYPE[unit.type]


def list_staff(db: Session, *, q: str | None, unit_id: int | None, limit: int | None,
               offset: int) -> Page[schemas.StaffOut]:
    page = staff_repository.search(db, q=q, unit_id=unit_id, limit=limit, offset=offset)
    return Page([staff_out(s) for s in page.items], page.total)


def create_staff(db: Session, body: schemas.StaffCreate) -> schemas.StaffOut:
    """Tao tai khoan can bo phong ban. Vai tro suy ra tu loai don vi (Khoa -> Van phong
    Khoa, hoac Lanh dao Khoa neu faculty_leader; P.Dao tao, P.CTSV, Ban nganh)."""
    account_service.ensure_email_available(db, body.email)
    unit = _get_unit(db, body.unit_id)
    user = account_service.new_user(db, email=body.email, password=body.password,
                                    role=role_for(unit, body.faculty_leader),
                                    full_name=body.full_name)
    staff = models.Staff(user_id=user.id, unit_id=unit.id, position=body.position)
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff_out(staff)


def update_staff(db: Session, staff_id: int, body: schemas.StaffUpdate) -> schemas.StaffOut:
    """Sua can bo; chuyen don vi thi vai tro doi theo loai don vi moi (co hieu luc ngay
    vi quyen luon doc tu DB, khong tu role trong token)."""
    staff = _get_or_404(db, staff_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("full_name"):
        staff.user.full_name = data["full_name"]
    if "position" in data and data["position"] is not None:
        staff.position = data["position"]
    if data.get("unit_id") is not None or data.get("faculty_leader") is not None:
        unit = _get_unit(db, data["unit_id"]) if data.get("unit_id") is not None else staff.unit
        leader = (data["faculty_leader"] if data.get("faculty_leader") is not None
                  else staff.user.role == ROLE_FACULTY_LEADER)
        staff.unit_id = unit.id
        staff.user.role = role_for(unit, leader)
    db.commit()
    db.refresh(staff)
    return staff_out(staff)


def delete_staff(db: Session, staff_id: int) -> dict:
    staff = _get_or_404(db, staff_id)
    user = staff.user
    account_service.ensure_no_attendance_edits(db, user.id)
    account_service.delete_profile_and_user(db, staff, user)
    db.commit()
    return {"ok": True}
