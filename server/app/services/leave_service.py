"""Don xin phep vang (PH6): SV nop -> GV day lop / Lanh dao Khoa duyet hoac tu choi (bat buoc ly do
khong hop le) -> he thong gui ket qua cho SV -> SV xac nhan da nhan ket qua.

Don duoc duyet cho buoi (lich hoc, ngay):
- neu phien cua buoi do DA ghi SV "vang" => doi ngay sang "vang co phep" (excused), luu lich su sua
  (attendance_audits) va bao phu huynh nhu moi lan doi trang thai;
- neu chua dong phien => khi dong phien (thu cong hay tu dong) SV duoc ghi excused thay vi absent
  (session_service.close_session).
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import can_review_leave, filter_leave_requests
from app.core.config import settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.db import models
from app.repositories import (class_repository, leave_repository, schedule_repository, session_repository,
                              student_repository)
from app.services import user_notify
from app.services.mappers import room_label

PRESENT_STATUSES = ("present", "late", "manual")


def leave_out(db: Session, leave: models.LeaveRequest) -> schemas.LeaveRequestOut:
    schedule = leave.schedule
    clazz = schedule.clazz
    attendance_status = None
    session = session_repository.get_for_schedule_on(db, schedule.id, leave.absence_date)
    if session is not None:
        record = session_repository.get_record_for(db, session.id, leave.student_id)
        attendance_status = record.status if record else None
    return schemas.LeaveRequestOut(
        id=leave.id, student_id=leave.student_id, student_code=leave.student.student_code,
        full_name=leave.student.user.full_name, schedule_id=schedule.id, class_id=clazz.id,
        class_code=clazz.class_code, subject_name=clazz.subject_name, absence_date=leave.absence_date,
        start_time=schedule.start_time, end_time=schedule.end_time, room=room_label(schedule),
        reason=leave.reason, status=leave.status, created_at=leave.created_at,
        reviewed_at=leave.reviewed_at, reviewer_name=leave.reviewer.full_name if leave.reviewer else None,
        review_note=leave.review_note, student_ack_at=leave.student_ack_at,
        attendance_status=attendance_status,
    )


def _own_student(db: Session, user: models.User) -> models.Student:
    student = student_repository.get_by_user(db, user.id)
    if not student:
        raise NotFoundError("Khong tim thay ho so sinh vien")
    return student


def _get_or_404(db: Session, leave_id: int) -> models.LeaveRequest:
    leave = leave_repository.get(db, leave_id)
    if not leave:
        raise NotFoundError("Don xin phep khong ton tai")
    return leave


def create(db: Session, user: models.User, body: schemas.LeaveRequestCreate) -> schemas.LeaveRequestOut:
    """SV nop don cho mot buoi hoc cua lop minh da ghi danh."""
    student = _own_student(db, user)
    schedule = schedule_repository.get(db, body.schedule_id)
    if not schedule:
        raise NotFoundError("Lich hoc khong ton tai")
    if not class_repository.is_enrolled(db, schedule.class_id, student.id):
        raise ForbiddenError("Ban khong ghi danh lop hoc phan nay")
    if body.absence_date.weekday() != schedule.weekday:
        raise BadRequestError("Ngay xin phep khong dung thu cua lich hoc nay")
    earliest = datetime.now().date() - timedelta(days=settings.LEAVE_REQUEST_MAX_PAST_DAYS)
    if body.absence_date < earliest:
        raise BadRequestError(
            f"Chi nop bo sung don cho buoi trong {settings.LEAVE_REQUEST_MAX_PAST_DAYS} ngay gan nhat")
    reason = body.reason.strip()
    if not reason:
        raise BadRequestError("Can nhap ly do xin phep")
    if leave_repository.find(db, student.id, schedule.id, body.absence_date):
        raise BadRequestError("Da co don xin phep cho buoi hoc nay")
    session = session_repository.get_for_schedule_on(db, schedule.id, body.absence_date)
    if session is not None:
        record = session_repository.get_record_for(db, session.id, student.id)
        if record is not None and record.status in PRESENT_STATUSES:
            raise BadRequestError("Ban da co mat o buoi hoc nay, khong can xin phep")

    leave = models.LeaveRequest(student_id=student.id, schedule_id=schedule.id,
                                absence_date=body.absence_date, reason=reason, status="pending",
                                review_note="")
    db.add(leave)
    clazz = schedule.clazz
    user_notify.notify(
        db, clazz.lecturer.user_id, user_notify.KIND_LEAVE_SUBMITTED,
        f"Đơn xin phép mới — {clazz.class_code}",
        f"{user.full_name} ({student.student_code}) xin phép vắng buổi "
        f"{body.absence_date:%d/%m/%Y} {schedule.start_time:%H:%M}–{schedule.end_time:%H:%M}. Lý do: {reason}",
        "/leave-requests")
    db.commit()
    db.refresh(leave)
    return leave_out(db, leave)


def list_requests(db: Session, user: models.User, *, status: str | None, class_id: int | None,
                  limit: int) -> list[schemas.LeaveRequestOut]:
    query = filter_leave_requests(leave_repository.base_query(db), user, db)
    return [leave_out(db, lv) for lv in leave_repository.search(query, status=status, class_id=class_id,
                                                                  limit=limit)]


def _check_reviewable(db: Session, user: models.User, leave: models.LeaveRequest) -> None:
    if not can_review_leave(user, leave, db):
        raise ForbiddenError("Khong co quyen duyet don xin phep nay")
    if leave.status != "pending":
        raise BadRequestError("Don xin phep da duoc xu ly truoc do")


def _apply_excused(db: Session, user: models.User, leave: models.LeaveRequest) -> None:
    """Phien cua buoi do da ghi SV vang => doi sang vang co phep, luu lich su sua."""
    session = session_repository.get_for_schedule_on(db, leave.schedule_id, leave.absence_date)
    if session is None:
        return
    record = session_repository.get_record_for(db, session.id, leave.student_id)
    if record is None or record.status != "absent":
        return
    record.status = "excused"
    db.add(models.AttendanceAudit(record_id=record.id, changed_by=user.id, old_status="absent",
                                  new_status="excused", reason=f"Đơn xin phép #{leave.id}: {leave.reason}"))


def approve(db: Session, user: models.User, leave_id: int, body: schemas.LeaveApprove) -> schemas.LeaveRequestOut:
    leave = _get_or_404(db, leave_id)
    _check_reviewable(db, user, leave)
    leave.status = "approved"
    leave.reviewed_by = user.id
    leave.reviewed_at = datetime.now()
    leave.review_note = body.note.strip()
    _apply_excused(db, user, leave)
    clazz = leave.schedule.clazz
    user_notify.notify(
        db, leave.student.user_id, user_notify.KIND_LEAVE_APPROVED,
        f"Đơn xin phép được duyệt — {clazz.class_code}",
        f"Đơn xin phép vắng buổi {leave.absence_date:%d/%m/%Y} đã được duyệt; buổi này được tính "
        f"vắng có phép.{' Ghi chú: ' + leave.review_note if leave.review_note else ''} "
        "Vui lòng xác nhận đã nhận kết quả.", "/leave-requests")
    db.commit()
    db.refresh(leave)
    return leave_out(db, leave)


def reject(db: Session, user: models.User, leave_id: int, body: schemas.LeaveReject) -> schemas.LeaveRequestOut:
    reason = body.reason.strip()
    if not reason:
        raise BadRequestError("Can nhap ly do khong hop le khi tu choi")
    leave = _get_or_404(db, leave_id)
    _check_reviewable(db, user, leave)
    leave.status = "rejected"
    leave.reviewed_by = user.id
    leave.reviewed_at = datetime.now()
    leave.review_note = reason
    clazz = leave.schedule.clazz
    user_notify.notify(
        db, leave.student.user_id, user_notify.KIND_LEAVE_REJECTED,
        f"Đơn xin phép không được duyệt — {clazz.class_code}",
        f"Đơn xin phép vắng buổi {leave.absence_date:%d/%m/%Y} không được duyệt. Lý do không hợp lệ: "
        f"{reason}. Vui lòng xác nhận đã nhận kết quả.", "/leave-requests")
    db.commit()
    db.refresh(leave)
    return leave_out(db, leave)


def acknowledge(db: Session, user: models.User, leave_id: int) -> schemas.LeaveRequestOut:
    """SV xac nhan da nhan ket qua duyet don cua minh."""
    student = _own_student(db, user)
    leave = leave_repository.get(db, leave_id)
    if leave is None or leave.student_id != student.id:
        raise NotFoundError("Don xin phep khong ton tai")
    if leave.status == "pending":
        raise BadRequestError("Don xin phep chua co ket qua duyet")
    if leave.student_ack_at is None:
        leave.student_ack_at = datetime.now()
        db.commit()
        db.refresh(leave)
    return leave_out(db, leave)
