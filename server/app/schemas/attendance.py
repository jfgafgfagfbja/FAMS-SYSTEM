"""Schema Pydantic - nhom attendance (tach tu app/schemas.py cua ban goc)."""
from datetime import date, time

from pydantic import BaseModel, ConfigDict

from app.core.media import SignedMediaUrl
from app.core.timeutil import LocalDateTime

__all__ = ["SessionCreate", "CheckinInfoOut", "SessionOut", "SessionDetail", "RecognizeResult", "SelfCheckinResult", "RecordOut", "RecordUpdate", "AttendanceAuditOut", "ManualCheck", "RosterEntryOut"]


# ---- Attendance ----
class SessionCreate(BaseModel):
    schedule_id: int
    session_date: date


class CheckinInfoOut(BaseModel):
    """Thong tin toi thieu SV can truoc khi tu diem danh - khong lo danh sach lop
    hay ket qua cua nguoi khac nhu SessionDetail."""
    session_id: int
    room: str


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int
    session_date: date
    status: str


class SessionDetail(BaseModel):
    """Chi tiet 1 phien diem danh, kem thong tin lop/lich de frontend dung
    (vd lay class_id de goi GET /classes/{class_id}/students lam danh sach lop)."""
    id: int
    schedule_id: int
    session_date: date
    status: str
    opened_at: LocalDateTime
    closed_at: LocalDateTime | None = None
    class_id: int
    class_code: str
    subject_name: str
    room: str
    start_time: time
    end_time: time
    lecturer_name: str | None = None
    # Het thoi diem nay (end_time + SESSION_GRACE_MINUTES) khong nhan diem danh nua.
    checkin_deadline: LocalDateTime | None = None
    location_name: str | None = None  # dia diem doi chieu GPS khi SV tu diem danh


class RecognizeResult(BaseModel):
    """Ket qua nhan dien 1 khuon mat trong frame."""
    student_id: int | None
    student_code: str | None
    full_name: str | None
    confidence: float
    status: str  # recognized | unknown | already_checked | spoof | confirming
    evidence_image: SignedMediaUrl = None  # URL /evidence/... (co chu ky) lam bang chung
    liveness_score: float | None = None  # diem "mat that" tu anti-spoofing
    bbox: list[int] | None = None  # [x1, y1, x2, y2] de frontend ve overlay
    confirm_count: int | None = None  # so frame da nhan dien trong phien (status=confirming)
    confirm_needed: int | None = None  # so frame can de xac nhan (settings.CONFIRM_FRAMES)


class SelfCheckinResult(BaseModel):
    """Ket qua khi SV tu chup selfie diem danh (chi so khop voi khuon mat cua
    CHINH SV do, khac voi RecognizeResult cua luong camera lop hoc quet nhieu mat)."""
    # recognized | already_checked | not_matched | no_face | multiple_faces | spoof
    # | consent_required | location_* (xem geo_service)
    status: str
    confidence: float = 0.0
    liveness_score: float | None = None
    evidence_image: SignedMediaUrl = None
    record_id: int | None = None
    record_status: str | None = None  # present | late (khi status=recognized/already_checked)
    message: str = ""
    distance_m: float | None = None       # khoang cach toi dia diem diem danh (neu doi chieu GPS)
    allowed_radius_m: float | None = None


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    checked_at: LocalDateTime
    status: str
    confidence: float
    evidence_image: SignedMediaUrl = ""
    source: str = "camera"
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None
    distance_m: float | None = None


class RecordUpdate(BaseModel):
    """Sua trang thai 1 record sau buoi hoc. Bat buoc co ly do de luu vao AttendanceAudit."""
    status: str  # present | late | absent | excused
    reason: str


class AttendanceAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    changed_by: int
    old_status: str
    new_status: str
    reason: str
    changed_at: LocalDateTime


class ManualCheck(BaseModel):
    student_id: int


class RosterEntryOut(BaseModel):
    """1 dong trong danh sach lop gop voi trang thai diem danh cua 1 phien cu the -
    tranh FE phai goi rieng danh sach lop + danh sach record roi tu ghep (N+1)."""
    student_id: int
    student_code: str
    full_name: str
    status: str | None = None  # None = chua diem danh
    confidence: float | None = None
    evidence_image: SignedMediaUrl = None
    checked_at: LocalDateTime | None = None
    record_id: int | None = None
    source: str | None = None  # camera | selfie | manual
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None
    distance_m: float | None = None
