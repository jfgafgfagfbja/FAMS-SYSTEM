"""Vong doi phien diem danh: mo phien (khung gio), xem/sua phien, ma QR, han nhan diem danh,
dong phien (sinh vang), tu dong dong phien bi quen."""
import logging
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, object_session

from app import schemas
from app.core.authz import ensure_class_access, ensure_class_view, filter_classes
from app.core.config import settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.db import models
from app.repositories import (class_repository, schedule_repository, session_repository,
                              student_repository)
from app.services import checkin_code_service
from app.services.attendance_stats import compute_class_attendance_stats
from app.services.geo_service import resolve_geofence
from app.services.mappers import room_label

logger = logging.getLogger(__name__)


# Dem so frame da nhan dien duoc 1 SV trong 1 phien, truoc khi ghi attendance record
# (multi-frame confirmation - giam nhan nham). Luu in-memory theo session_id, KHONG
# ben vung: mat het khi restart server (chap nhan duoc vi chi anh huong phien dang
# mo tai thoi diem restart, SV se phai duoc nhan dien lai tu dau). Don khi dong phien.
_confirm_counts: dict[int, dict[int, int]] = {}


def get_or_404(db: Session, session_id: int) -> models.AttendanceSession:
    session = session_repository.get(db, session_id)
    if not session:
        raise NotFoundError("Phien khong ton tai")
    return session


def checkin_deadline(session: models.AttendanceSession) -> datetime:
    """Sau thoi diem nay (gio ket thuc tiet + SESSION_GRACE_MINUTES) khong nhan diem danh."""
    end = datetime.combine(session.session_date, session.schedule.end_time)
    return end + timedelta(minutes=settings.SESSION_GRACE_MINUTES)


def ensure_accepting_checkins(session: models.AttendanceSession) -> None:
    if session.status != "open":
        raise NotFoundError("Phien khong ton tai hoac da dong")
    if datetime.now() > checkin_deadline(session):
        raise BadRequestError("Da het gio nhan diem danh cho phien nay")


def session_detail(session: models.AttendanceSession) -> schemas.SessionDetail:
    clazz = session.schedule.clazz
    fence = resolve_geofence(object_session(session), session.schedule)
    return schemas.SessionDetail(
        id=session.id, schedule_id=session.schedule_id,
        session_date=session.session_date, status=session.status,
        opened_at=session.opened_at, closed_at=session.closed_at,
        class_id=clazz.id, class_code=clazz.class_code, subject_name=clazz.subject_name,
        room=room_label(session.schedule), start_time=session.schedule.start_time,
        end_time=session.schedule.end_time,
        lecturer_name=clazz.lecturer.user.full_name if clazz.lecturer else None,
        checkin_deadline=checkin_deadline(session),
        location_name=fence.name if fence else None,
        require_qr=session.require_qr,
    )


def open_session(db: Session, user: models.User, body: schemas.SessionCreate) -> models.AttendanceSession:
    """Mo phien diem danh. Chi cho mo khi: dung ngay hom nay, dung thu cua lich hoc,
    trong khung [start_time - EARLY_OPEN_MINUTES, end_time] va chua co phien nao cua
    cung lich hoc trong ngay (moi rang buoc sai tra 400 voi message rieng)."""
    schedule = schedule_repository.get(db, body.schedule_id)
    if not schedule:
        raise NotFoundError("Lich hoc khong ton tai")
    ensure_class_access(user, schedule.class_id, db)

    now = datetime.now()
    if body.session_date != now.date():
        raise BadRequestError("Chi duoc mo phien diem danh cho ngay hom nay")
    if body.session_date.weekday() != schedule.weekday:
        raise BadRequestError("Ngay diem danh khong dung thu cua lich hoc nay")

    open_from = datetime.combine(body.session_date, schedule.start_time) - timedelta(
        minutes=settings.EARLY_OPEN_MINUTES)
    if now < open_from:
        raise BadRequestError(f"Chua den gio - chi mo duoc phien tu {open_from:%H:%M}")
    if now > datetime.combine(body.session_date, schedule.end_time):
        raise BadRequestError("Tiet hoc da ket thuc, khong the mo phien diem danh")

    if session_repository.get_for_schedule_on(db, body.schedule_id, body.session_date):
        raise BadRequestError("Da co phien diem danh cho lich hoc nay trong ngay hom nay")

    session = models.AttendanceSession(
        schedule_id=body.schedule_id, session_date=body.session_date,
        require_qr=(settings.SELF_CHECKIN_REQUIRE_QR_DEFAULT if body.require_qr is None
                    else body.require_qr),
    )
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        # 2 request mo phien gan nhu dong thoi: kiem tra o tren deu chua thay phien nao,
        # UNIQUE(schedule_id, session_date) o DB chan request den sau.
        db.rollback()
        raise BadRequestError("Da co phien diem danh cho lich hoc nay trong ngay hom nay")
    db.refresh(session)
    return session


def list_sessions(db: Session, user: models.User, *, status: str | None, class_id: int | None,
                  limit: int | None) -> list[schemas.SessionDetail]:
    """Phien trong pham vi xem lop cua user (GV: lop minh day, Khoa: lop Khoa quan ly)."""
    sessions = session_repository.search(
        db, scope=lambda query: filter_classes(query, user, db), status=status,
        class_id=class_id, limit=limit)
    return [session_detail(s) for s in sessions]


def get_session(db: Session, user: models.User, session_id: int) -> schemas.SessionDetail:
    session = get_or_404(db, session_id)
    ensure_class_view(user, session.schedule.class_id, db)
    return session_detail(session)


def update_session(db: Session, user: models.User, session_id: int,
                   body: schemas.SessionUpdate) -> schemas.SessionDetail:
    """Bat/tat yeu cau quet ma QR cho buoi dang dien ra."""
    session = get_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    if session.status != "open":
        raise BadRequestError("Phien da dong, khong sua duoc")
    session.require_qr = body.require_qr
    db.commit()
    db.refresh(session)
    return session_detail(session)


def checkin_info(db: Session, user: models.User, session_id: int) -> schemas.CheckinInfoOut:
    """SV xem buoi nay co bat buoc quet ma QR khong, truoc khi chup anh."""
    session = get_or_404(db, session_id)
    student = student_repository.get_by_user(db, user.id)
    if not student or not class_repository.is_enrolled(db, session.schedule.class_id, student.id):
        raise ForbiddenError("Ban khong ghi danh lop hoc phan nay")
    return schemas.CheckinInfoOut(session_id=session.id, require_qr=session.require_qr,
                                  room=room_label(session.schedule))


def checkin_code(db: Session, user: models.User, session_id: int) -> schemas.CheckinCodeOut:
    """Ma QR dang hieu luc cua phien. Chi nguoi day/quan ly lop xem duoc - SV lay duoc ma qua
    API thi khong can co mat trong phong, mat het y nghia cua viec quet ma."""
    session = get_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    if session.status != "open":
        raise BadRequestError("Phien da dong, khong con ma diem danh")
    code = checkin_code_service.current_code(session.id)
    return schemas.CheckinCodeOut(
        session_id=session.id, qr_payload=code.qr_payload, digits=code.digits,
        rotate_seconds=code.rotate_seconds, expires_in_seconds=code.expires_in_seconds)


def close_session(db: Session, session: models.AttendanceSession) -> dict:
    """Dong phien: SV ghi danh chua co record -> absent. Tra kem danh sach SV vua vuot
    nguong canh bao chuyen can do phien nay (so voi truoc khi dong)."""
    class_id = session.schedule.class_id

    # Chup lai trang thai canh bao TRUOC khi dong phien, de sau do biet SV nao
    # "vua" vuot nguong (co the vi bi diem danh vang hoac chi vi tong so buoi tang len).
    warned_before = {
        r["student_id"] for r in compute_class_attendance_stats(db, class_id) if r["warning"]
    }

    checked_ids = {r.student_id for r in session.records}
    absent_count = 0
    for student_id in class_repository.enrolled_student_ids(db, class_id):
        if student_id not in checked_ids:
            db.add(models.AttendanceRecord(
                session_id=session.id, student_id=student_id, status="absent"))
            absent_count += 1

    session.status = "closed"
    session.closed_at = datetime.now()
    db.commit()
    _confirm_counts.pop(session.id, None)

    newly_warned = [
        r for r in compute_class_attendance_stats(db, class_id)
        if r["warning"] and r["student_id"] not in warned_before
    ]
    return {"ok": True, "absent": absent_count,
            "present": len(checked_ids), "newly_warned": newly_warned}


def close_session_by_user(db: Session, user: models.User, session_id: int) -> dict:
    session = get_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    if session.status != "open":
        raise BadRequestError("Phien diem danh da dong truoc do")
    return close_session(db, session)


def auto_close_expired_sessions(db: Session, now: datetime | None = None) -> int:
    """Dong cac phien van mo sau han nhan diem danh (GV quen bam Dong phien)."""
    now = now or datetime.now()
    closed = 0
    for session in session_repository.open_sessions(db):
        if now > checkin_deadline(session):
            close_session(db, session)
            closed += 1
            logger.info("Tu dong dong phien diem danh id=%s (qua han %s)",
                        session.id, checkin_deadline(session))
    return closed
