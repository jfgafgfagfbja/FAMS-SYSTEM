"""Schema Pydantic - nhom reports (tach tu app/schemas.py cua ban goc)."""
from datetime import date

from pydantic import BaseModel

from app.core.media import SignedMediaUrl
from app.core.timeutil import LocalDateTime

__all__ = ["MyAttendanceSessionOut", "MyClassAttendanceOut", "OverviewStats", "OverviewFacultyRow", "OverviewOut"]


class MyAttendanceSessionOut(BaseModel):
    """1 buoi hoc trong 1 lop, dung khi SV mo rong chi tiet tren trang chuyen can."""
    session_id: int
    session_date: date
    status: str | None = None  # None = SV chua co record cho buoi nay
    checked_at: LocalDateTime | None = None
    confidence: float | None = None
    evidence_image: SignedMediaUrl = None
    record_id: int | None = None
    source: str | None = None  # camera | selfie | manual
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None
    distance_m: float | None = None


class MyClassAttendanceOut(BaseModel):
    """Chuyen can 1 lop hoc phan trong 1 hoc ky cua 1 SV."""
    class_id: int
    class_code: str
    subject_name: str
    semester: str
    lecturer_name: str
    lecturer_email: str
    present: int
    late: int
    absent: int
    excused: int
    manual: int
    total_sessions: int
    absent_ratio: float
    warn_ratio: float  # settings.ABSENCE_WARN_RATIO - de FE tinh nguong "sap cam thi" ma khong hardcode
    warning: bool
    sessions: list[MyAttendanceSessionOut]


# ---- Thong ke tong hop ----
class OverviewStats(BaseModel):
    classes: int
    students: int
    lecturers: int
    closed_sessions: int
    records: int
    present: int
    late: int
    manual: int
    absent: int
    excused: int
    attendance_rate: float  # (present + late + manual) / records
    absent_rate: float      # absent / records
    warned_students: int    # so SV vuot nguong vang o it nhat 1 lop


class OverviewFacultyRow(OverviewStats):
    faculty_id: int | None
    faculty_code: str | None
    faculty_name: str


class OverviewOut(BaseModel):
    """Thong ke chuyen can tong hop - CHI so lieu, khong ten/anh (dung cho Ban nganh)."""
    scope: str  # school | faculty
    scope_name: str
    semester: str | None
    semesters: list[str]
    totals: OverviewStats
    by_faculty: list[OverviewFacultyRow]
