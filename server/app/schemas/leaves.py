"""Schema Pydantic - don xin phep vang (PH6)."""
from datetime import date, time

from pydantic import BaseModel

from app.core.timeutil import LocalDateTime

__all__ = ["LeaveRequestCreate", "LeaveApprove", "LeaveReject", "LeaveRequestOut"]


class LeaveRequestCreate(BaseModel):
    """SV xin phep vang mot buoi hoc: lich hoc (lop + thu + gio) va ngay cu the."""
    schedule_id: int
    absence_date: date
    reason: str


class LeaveApprove(BaseModel):
    note: str = ""  # ghi chu tuy chon cua nguoi duyet


class LeaveReject(BaseModel):
    reason: str  # ly do khong hop le - bat buoc


class LeaveRequestOut(BaseModel):
    id: int
    student_id: int
    student_code: str
    full_name: str
    schedule_id: int
    class_id: int
    class_code: str
    subject_name: str
    absence_date: date
    start_time: time
    end_time: time
    room: str
    reason: str
    status: str  # pending | approved | rejected
    created_at: LocalDateTime
    reviewed_at: LocalDateTime | None = None
    reviewer_name: str | None = None
    review_note: str = ""
    student_ack_at: LocalDateTime | None = None
    # Trang thai diem danh cua SV o buoi do (neu phien da co ban ghi): absent / excused / ...
    attendance_status: str | None = None
