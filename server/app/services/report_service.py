"""Nghiep vu bao cao, thong ke chuyen can (PH8).

Quy tac chung: chi tinh phien DA DONG; ti le vang = so buoi absent / tong phien da dong;
"excused" (co phep) khong tinh la vang; canh bao khi ti le >= ABSENCE_WARN_RATIO.
"""
import io
from dataclasses import dataclass

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import ensure_class_view, ensure_student_view, staff_unit_id
from app.core.config import settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.db import models
from app.db.models import FACULTY_ROLES, ROLE_STUDENT
from app.repositories import (class_repository, lecturer_repository, report_repository,
                              session_repository, student_repository, unit_repository)
from app.services import audit
from app.services.attendance_stats import STATUSES, compute_class_attendance_stats

STATUS_LETTER = {"present": "P", "late": "L", "absent": "A", "excused": "E", "manual": "M"}
RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ---------------- Chuyen can cua mot sinh vien ----------------

def student_attendance(db: Session, student: models.Student,
                       semester: str | None) -> list[schemas.MyClassAttendanceOut]:
    """Chuyen can chi tiet cua 1 SV, loc theo hoc ky (Class.semester, dang luu "YYYY.N").
    Khong truyen semester -> lay hoc ky moi nhat (so sanh chuoi) trong cac lop da ghi danh.
    Gom san danh sach tung buoi hoc (ngay, trang thai, gio ghi nhan, anh bang chung, vi tri
    GPS neu la selfie) trong 1 lan goi, tranh N+1.

    Dung chung cho SV tu xem, phu huynh xem con va phong ban xem 1 SV."""
    enrollments = student.enrollments
    if not enrollments:
        return []

    target_semester = semester or max((e.clazz.semester for e in enrollments), default=None)
    if not target_semester:
        return []

    result = []
    for enrollment in enrollments:
        clazz = enrollment.clazz
        if clazz.semester != target_semester:
            continue

        sessions = session_repository.closed_of_class(db, clazz.id)
        records_by_session = {}
        if sessions:
            records_by_session = {
                r.session_id: r
                for r in session_repository.records_of_student_in(db, student.id,
                                                                  [s.id for s in sessions])
            }

        counts = {"present": 0, "late": 0, "absent": 0, "excused": 0, "manual": 0}
        session_details = []
        for s in sessions:
            r = records_by_session.get(s.id)
            if r:
                counts[r.status] = counts.get(r.status, 0) + 1
            session_details.append(schemas.MyAttendanceSessionOut(
                session_id=s.id, session_date=s.session_date,
                status=r.status if r else None,
                checked_at=r.checked_at if r else None,
                confidence=r.confidence if r else None,
                evidence_image=r.evidence_image if r else None,
                record_id=r.id if r else None,
                source=r.source if r else None,
                latitude=r.latitude if r else None,
                longitude=r.longitude if r else None,
                location_accuracy=r.location_accuracy if r else None,
                distance_m=r.distance_m if r else None,
            ))

        total_sessions = len(sessions)
        absent_ratio = counts["absent"] / total_sessions if total_sessions else 0
        lecturer = lecturer_repository.get(db, clazz.lecturer_id)
        result.append(schemas.MyClassAttendanceOut(
            class_id=clazz.id, class_code=clazz.class_code, subject_name=clazz.subject_name,
            semester=clazz.semester, lecturer_name=lecturer.user.full_name,
            lecturer_email=lecturer.user.email,
            **counts, total_sessions=total_sessions, absent_ratio=absent_ratio,
            warn_ratio=settings.ABSENCE_WARN_RATIO,
            warning=absent_ratio >= settings.ABSENCE_WARN_RATIO,
            sessions=session_details,
        ))
    return result


def _own_student(db: Session, user: models.User) -> models.Student:
    if user.role != ROLE_STUDENT:
        raise ForbiddenError("Chi sinh vien moi xem duoc muc nay")
    student = student_repository.get_by_user(db, user.id)
    if not student:
        raise NotFoundError("Khong tim thay ho so sinh vien")
    return student


def my_attendance_detail(db: Session, user: models.User,
                         semester: str | None) -> list[schemas.MyClassAttendanceOut]:
    return student_attendance(db, _own_student(db, user), semester)


def student_attendance_for_viewer(db: Session, user: models.User, student_id: int,
                                  semester: str | None) -> list[schemas.MyClassAttendanceOut]:
    """Phong ban/Khoa xem chuyen can chi tiet 1 SV (vd de duyet don xin phep)."""
    student = ensure_student_view(user, student_id, db)
    return student_attendance(db, student, semester)


def my_attendance_summary(db: Session, user: models.User) -> list[dict]:
    """Sinh vien tu xem tom tat chuyen can theo tung lop da dang ky (chi tinh phien da dong)."""
    student = _own_student(db, user)
    result = []
    for enrollment in student.enrollments:
        clazz = enrollment.clazz
        total_sessions = report_repository.count_closed_sessions(db, clazz.id)
        counts = {s: 0 for s in STATUSES}
        for status, cnt in report_repository.status_counts_of_student(db, clazz.id, student.id):
            counts[status] = cnt

        # excused khong tinh la vang khi xet canh bao chuyen can
        absent_ratio = counts["absent"] / total_sessions if total_sessions else 0
        result.append({
            "class_id": clazz.id,
            "class_code": clazz.class_code,
            "subject_name": clazz.subject_name,
            "semester": clazz.semester,
            **counts,
            "total_sessions": total_sessions,
            "warning": absent_ratio >= settings.ABSENCE_WARN_RATIO,
        })
    return result


# ---------------- Theo lop ----------------

def class_attendance(db: Session, user: models.User, class_id: int) -> list[dict]:
    """Thong ke chuyen can theo lop: ti le vang tung SV + canh bao."""
    ensure_class_view(user, class_id, db)
    return compute_class_attendance_stats(db, class_id)


def attendance_warnings(db: Session, user: models.User, class_id: int) -> list[dict]:
    """SV vuot nguong vang (absent / tong buoi da hoc >= ABSENCE_WARN_RATIO)."""
    ensure_class_view(user, class_id, db)
    return [r for r in compute_class_attendance_stats(db, class_id) if r["warning"]]


@dataclass
class ExcelFile:
    content: io.BytesIO
    filename: str
    media_type: str = XLSX_MEDIA_TYPE


def export_attendance(db: Session, user: models.User, class_id: int, semester: str) -> ExcelFile:
    """File Excel diem danh: sheet 1 la ma tran SV x buoi hoc, sheet 2 la thong ke tong hop
    lop. Ghi nhat ky vi du lieu ca nhan (ten, MSSV, ket qua) roi khoi he thong."""
    clazz = ensure_class_view(user, class_id, db)
    if clazz.semester != semester:
        raise BadRequestError(
            f"Lop {clazz.class_code} thuoc hoc ky {clazz.semester}, khong phai {semester}")

    sessions = session_repository.closed_of_class(db, class_id)
    students = class_repository.students_of_class(db, class_id)
    records = report_repository.closed_records_of_class(db, class_id)
    record_by_session_student = {(r.session_id, r.student_id): r.status for r in records}

    total_sessions = len(sessions)

    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Diem danh"

    header = (["MSSV", "Ho ten"]
              + [s.session_date.strftime("%d/%m/%Y") for s in sessions]
              + ["Tong vang", "% vang"])
    ws1.append(header)
    for cell in ws1[1]:
        cell.font = Font(bold=True)

    warning_count = 0
    for student in students:
        row = [student.student_code, student.user.full_name]
        absent_count = 0
        for session in sessions:
            status = record_by_session_student.get((session.id, student.id))
            row.append(STATUS_LETTER.get(status, ""))
            if status == "absent":
                absent_count += 1
        ratio = absent_count / total_sessions if total_sessions else 0
        row.append(absent_count)
        row.append(f"{ratio * 100:.1f}%")
        ws1.append(row)

        if ratio >= settings.ABSENCE_WARN_RATIO:
            warning_count += 1
            for cell in ws1[ws1.max_row]:
                cell.fill = RED_FILL

    for col in ws1.columns:
        values = [str(c.value) for c in col if c.value is not None]
        width = max((len(v) for v in values), default=10)
        ws1.column_dimensions[col[0].column_letter].width = width + 2

    ws2 = wb.create_sheet("Thong ke lop")
    summary_rows = [
        ("Ma lop", clazz.class_code),
        ("Mon hoc", clazz.subject_name),
        ("Hoc ky", clazz.semester),
        ("Khoa", clazz.faculty.name if clazz.faculty else ""),
        ("Tong so sinh vien", len(students)),
        ("Tong so buoi da diem danh", total_sessions),
        ("So SV vuot nguong canh bao vang", warning_count),
        ("Nguong canh bao (%)", f"{settings.ABSENCE_WARN_RATIO * 100:.0f}%"),
    ]
    for label, value in summary_rows:
        ws2.append([label, value])
    for row in ws2.iter_rows(min_row=1, max_row=len(summary_rows), min_col=1, max_col=1):
        for cell in row:
            cell.font = Font(bold=True)
    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 20

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    audit.record_event(db, "report.exported", target_type="class", target_id=clazz.id,
                       target_label=clazz.class_code, detail={"semester": semester})
    db.commit()
    return ExcelFile(buffer, f"diemdanh_{clazz.class_code}_{semester}.xlsx")


# ---------------- Thong ke tong hop ----------------

def _aggregate(db: Session, classes: list[models.Class]) -> dict:
    """So lieu chuyen can gop cho 1 nhom lop (khong kem ten/anh)."""
    class_ids = [c.id for c in classes]
    empty = {"classes": 0, "students": 0, "lecturers": 0, "closed_sessions": 0, "records": 0,
             **{s: 0 for s in STATUSES}, "attendance_rate": 0.0, "absent_rate": 0.0,
             "warned_students": 0}
    if not class_ids:
        return empty

    closed_sessions = report_repository.count_closed_sessions_of(db, class_ids)
    counts = {s: 0 for s in STATUSES}
    for status, cnt in report_repository.status_counts_of_classes(db, class_ids):
        counts[status] = cnt
    records = sum(counts.values())

    students = report_repository.distinct_students_of(db, class_ids)
    warned = {
        r["student_id"]
        for c in classes
        for r in compute_class_attendance_stats(db, c.id)
        if r["warning"]
    }
    attended = counts["present"] + counts["late"] + counts["manual"]
    return {
        "classes": len(classes), "students": students,
        "lecturers": len({c.lecturer_id for c in classes}),
        "closed_sessions": closed_sessions, "records": records, **counts,
        "attendance_rate": round(attended / records, 4) if records else 0.0,
        "absent_rate": round(counts["absent"] / records, 4) if records else 0.0,
        "warned_students": len(warned),
    }


def overview(db: Session, user: models.User, semester: str | None) -> schemas.OverviewOut:
    """Thong ke chuyen can tong hop theo hoc ky, chia theo Khoa. Chi so lieu (khong ten,
    khong anh) nen Ban nganh cung xem duoc; can bo Khoa chi thay Khoa cua minh.
    Khong truyen semester -> hoc ky moi nhat co lop hoc phan."""
    if user.role in FACULTY_ROLES:
        unit_id = staff_unit_id(user, db)
        unit = unit_repository.get(db, unit_id) if unit_id else None
        faculty_scope = unit_id or -1
        scope, scope_name = "faculty", unit.name if unit else "Chua gan don vi"
    else:
        faculty_scope = None
        scope, scope_name = "school", "Toan truong"

    semesters = class_repository.semesters(db, faculty_scope)
    target = semester or (semesters[0] if semesters else None)
    classes = class_repository.of_semester(db, target, faculty_scope) if target else []

    by_faculty: dict[int | None, list[models.Class]] = {}
    for c in classes:
        by_faculty.setdefault(c.faculty_id, []).append(c)

    faculty_rows = []
    for faculty_id, group in by_faculty.items():
        unit = unit_repository.get(db, faculty_id) if faculty_id else None
        faculty_rows.append(schemas.OverviewFacultyRow(
            faculty_id=faculty_id,
            faculty_code=unit.code if unit else None,
            faculty_name=unit.name if unit else "Chua gan Khoa",
            **_aggregate(db, group),
        ))
    faculty_rows.sort(key=lambda r: (r.faculty_id is None, r.faculty_name))

    return schemas.OverviewOut(
        scope=scope, scope_name=scope_name, semester=target, semesters=semesters,
        totals=schemas.OverviewStats(**_aggregate(db, classes)),
        by_faculty=faculty_rows,
    )
