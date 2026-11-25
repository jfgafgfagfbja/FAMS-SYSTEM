"""Thong bao toi mot nguoi dung cu the, ngoai luong "con duoc diem danh" cua parent_notify:

- ket qua duyet khuon mat (P.CTSV) va ket qua duyet don xin phep vang (GV lop / Lanh dao Khoa)
  gui cho SINH VIEN - SV xac nhan da nhan ket qua o chuc nang tuong ung;
- don xin phep moi gui cho GIANG VIEN day lop;
- canh bao vang sau thong ke (dong phien lam SV vuot nguong) gui cho SINH VIEN va PHU HUYNH.

Thong bao vao hop thu trong app (bang notifications). Rieng phu huynh: neu bat nhan email va may
chu co SMTP thi dua vao hang doi email (tac vu nen parent_notify.send_pending_emails gui sau).
"""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.services import email_service

KIND_FACE_APPROVED = "face_approved"
KIND_FACE_REJECTED = "face_rejected"
KIND_LEAVE_SUBMITTED = "leave_submitted"
KIND_LEAVE_APPROVED = "leave_approved"
KIND_LEAVE_REJECTED = "leave_rejected"
KIND_ABSENCE_WARNING = "absence_warning"


def notify(db: Session, user_id: int, kind: str, title: str, body: str, link: str | None,
           *, email: bool = False) -> models.Notification:
    """Them 1 thong bao (chua commit - di cung giao dich cua nghiep vu goi toi)."""
    wants_email = email and email_service.is_configured()
    notification = models.Notification(
        user_id=user_id, kind=kind, title=title, body=body, link=link,
        email_status="pending" if wants_email else "skipped")
    db.add(notification)
    return notification


def notify_absence_warnings(db: Session, clazz: models.Class, rows: list[dict]) -> int:
    """Sau khi thong ke lai chuyen can (dong phien), bao cho SV vua vuot nguong vang va phu huynh
    cua SV do. rows: cac dong cua compute_class_attendance_stats co warning=True."""
    sent = 0
    threshold = round(settings.ABSENCE_WARN_RATIO * 100)
    for row in rows:
        student = db.get(models.Student, row["student_id"])
        if student is None:
            continue
        ratio = round(row["absent_ratio"] * 100, 1)
        detail = (f"vắng {row['absent']}/{row['total_sessions']} buổi đã điểm danh "
                  f"({ratio}%), vượt ngưỡng cảnh báo {threshold}% của lớp {clazz.class_code} — "
                  f"{clazz.subject_name}.")
        notify(db, student.user_id, KIND_ABSENCE_WARNING, f"Cảnh báo chuyên cần — {clazz.class_code}",
               f"Bạn đã {detail} Vắng có phép không bị tính.", "/my-attendance")
        sent += 1
        for link in db.query(models.ParentStudent).filter_by(student_id=student.id).all():
            parent = link.parent
            notify(db, parent.user_id, KIND_ABSENCE_WARNING,
                   f"Cảnh báo chuyên cần: {student.user.full_name} — {clazz.class_code}",
                   f"{student.user.full_name} ({student.student_code}) đã {detail}",
                   f"/children/{student.id}", email=parent.notify_email and bool(parent.user.email))
            sent += 1
    return sent
