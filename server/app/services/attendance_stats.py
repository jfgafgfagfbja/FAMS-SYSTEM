"""Thong ke chuyen can dung chung cho bao cao, dong phien va thong ke tong hop."""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories import report_repository, student_repository

STATUSES = ("present", "late", "absent", "excused", "manual")


def compute_class_attendance_stats(db: Session, class_id: int) -> list[dict]:
    """Thong ke chuyen can tung SV trong lop: so buoi present/late/absent/excused/manual,
    ti le vang (khong tinh excused) va co vuot ABSENCE_WARN_RATIO hay khong.

    Chi tinh phien DA DONG - ca tu so (so buoi) lan mau so (tong buoi), tranh ti le lech
    khi dang co phien mo (record co mat da ghi nhung phien chua duoc tinh vao tong).
    """
    total_sessions = report_repository.count_closed_sessions(db, class_id)
    rows = report_repository.status_counts_by_student(db, class_id)

    stats: dict[int, dict] = {}
    for student_id, status, cnt in rows:
        stats.setdefault(student_id, {s: 0 for s in STATUSES})
        stats[student_id][status] = cnt

    result = []
    for student_id, s in stats.items():
        student = student_repository.get(db, student_id)
        # excused khong tinh la vang khi xet canh bao chuyen can
        absent_ratio = s["absent"] / total_sessions if total_sessions else 0
        result.append({
            "student_id": student_id,
            "student_code": student.student_code,
            "full_name": student.user.full_name,
            **s,
            "total_sessions": total_sessions,
            "absent_ratio": round(absent_ratio, 4),
            "warning": absent_ratio >= settings.ABSENCE_WARN_RATIO,
        })
    result.sort(key=lambda r: r["student_code"])
    return result
