"""Chuyen ORM -> schema tra ve client, dung chung giua cac service (tranh lap lai va lech
du lieu giua cac endpoint tra cung mot loai doi tuong)."""
from app import schemas
from app.core.config import settings
from app.db import models


def face_status_of(student: models.Student) -> str:
    statuses = {e.status for e in student.embeddings}
    for status in ("approved", "pending", "rejected"):
        if status in statuses:
            return status
    return "none"


def student_out(s: models.Student, out_cls=schemas.StudentOut, **extra):
    return out_cls(
        id=s.id, student_code=s.student_code, full_name=s.user.full_name,
        major=s.major, cohort=s.cohort,
        face_enrolled=any(e.status == "approved" for e in s.embeddings),
        face_status=face_status_of(s),
        consent_given=s.consent_given, consent_version=s.consent_version,
        consent_method=s.consent_method, consent_recorded_by=s.consent_recorded_by,
        faculty_id=s.faculty_id, faculty_name=s.faculty.name if s.faculty else None,
        email=s.user.email,
        **extra,
    )


def lecturer_out(l: models.Lecturer) -> schemas.LecturerOut:
    return schemas.LecturerOut(
        id=l.id, lecturer_code=l.lecturer_code, full_name=l.user.full_name,
        department=l.department, email=l.user.email,
        faculty_id=l.faculty_id, faculty_name=l.faculty.name if l.faculty else None,
    )


def class_out(c: models.Class, student_count: int | None = None) -> schemas.ClassOut:
    return schemas.ClassOut(
        id=c.id, class_code=c.class_code, subject_name=c.subject_name,
        lecturer_id=c.lecturer_id, semester=c.semester, faculty_id=c.faculty_id,
        lecturer_name=c.lecturer.user.full_name if c.lecturer else None,
        faculty_name=c.faculty.name if c.faculty else None,
        student_count=student_count,
    )


def staff_out(st: models.Staff) -> schemas.StaffOut:
    return schemas.StaffOut(
        id=st.id, user_id=st.user_id, email=st.user.email, full_name=st.user.full_name,
        role=st.user.role, unit_id=st.unit_id, unit_code=st.unit.code,
        unit_name=st.unit.name, unit_type=st.unit.type, position=st.position,
    )


def room_label(schedule: models.Schedule) -> str:
    """Ten phong de hien thi: uu tien danh muc phong, con lai lay ten phong tu nhap cua lich."""
    return schedule.classroom.name if schedule.classroom is not None else (schedule.room or "")


def room_code(schedule: models.Schedule) -> str:
    """Ma phong cho truong `room` cua API (giu nhu truoc khi chuan hoa): ten tu nhap, hoac ma
    phong trong danh muc - CSDL khong con luu ban sao ma phong trong schedules.room."""
    if schedule.room:
        return schedule.room
    return schedule.classroom.code if schedule.classroom is not None else ""


def schedule_out(s: models.Schedule) -> schemas.ScheduleOut:
    return schemas.ScheduleOut(
        id=s.id, class_id=s.class_id, weekday=s.weekday,
        start_time=s.start_time, end_time=s.end_time,
        room=room_code(s), room_id=s.room_id,
        room_name=s.classroom.name if s.classroom else None,
        location_id=s.location_id,
    )


def room_out(room: models.Room, schedule_count: int = 0) -> schemas.RoomOut:
    has_own_point = room.latitude is not None and room.longitude is not None
    return schemas.RoomOut(
        id=room.id, code=room.code, name=room.name,
        location_id=room.location_id,
        location_name=room.location.name if room.location else None,
        building=room.building, floor=room.floor, capacity=room.capacity,
        latitude=room.latitude, longitude=room.longitude, radius_m=room.radius_m,
        is_active=room.is_active,
        effective_radius_m=(max(room.radius_m or 0.0, settings.ROOM_MIN_RADIUS_M)
                            if has_own_point else
                            (room.location.radius_m if room.location else None)),
        schedule_count=schedule_count,
    )
