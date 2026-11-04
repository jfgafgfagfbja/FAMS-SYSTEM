"""Nghiep vu lich hoc: xep lich (chong trung phong), tra cuu, lich tuan, lich day hom nay."""
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import can_view_class, ensure_class_manage, filter_classes
from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.db import models
from app.db.models import (FACULTY_ROLES, ROLE_ADMIN, ROLE_AFFAIRS, ROLE_LECTURER, ROLE_STUDENT,
                           ROLE_TRAINING)
from app.repositories import (class_repository, location_repository, room_repository,
                              schedule_repository, session_repository, student_repository)
from app.repositories.base import Page
from app.services import class_service
from app.services.geo_service import Geofence, default_location, resolve_geofence
from app.services.mappers import room_label, schedule_out


def open_from_time(start: time) -> time:
    """Gio som nhat duoc mo phien cho tiet bat dau luc `start`
    (= start - EARLY_OPEN_MINUTES). Dung chung cho cac response tra lich ve client."""
    anchor = datetime.combine(date(2000, 1, 1), start)
    return (anchor - timedelta(minutes=settings.EARLY_OPEN_MINUTES)).time()


# ---------------- Xep lich (thuoc lop hoc phan) ----------------

def _validate_location(db: Session, location_id: int | None) -> None:
    if location_id is not None and not location_repository.get(db, location_id):
        raise BadRequestError("Dia diem khong ton tai")


def _validate_room(db: Session, room_id: int | None) -> models.Room | None:
    if room_id is None:
        return None
    room = room_repository.get(db, room_id)
    if not room:
        raise BadRequestError("Phong hoc khong ton tai")
    if not room.is_active:
        raise BadRequestError(f"Phong {room.name} da ngung su dung, hay chon phong khac")
    return room


def _ensure_room_free(db: Session, room_id: int | None, weekday: int,
                      start: time, end: time, exclude_id: int | None = None) -> None:
    """Mot phong khong the chua 2 lop cung thu, trung khung gio - loi hay gap khi xep
    thoi khoa bieu. Hai tiet lien nhau (ket thuc = bat dau) van hop le."""
    if room_id is None:
        return
    clash = schedule_repository.find_room_clash(db, room_id, weekday, start, end, exclude_id)
    if clash is None:
        return
    raise BadRequestError(
        f"Phong nay da co lop {clash.clazz.class_code} hoc "
        f"{clash.start_time.strftime('%H:%M')}-{clash.end_time.strftime('%H:%M')} cung thu")


def _get_or_404(db: Session, schedule_id: int) -> models.Schedule:
    sched = schedule_repository.get(db, schedule_id)
    if not sched:
        raise NotFoundError("Lich hoc khong ton tai")
    return sched


def create_schedule(db: Session, user: models.User, body: schemas.ScheduleCreate) -> schemas.ScheduleOut:
    ensure_class_manage(user, class_service.get_or_404(db, body.class_id), db)
    _validate_location(db, body.location_id)
    room = _validate_room(db, body.room_id)
    _ensure_room_free(db, body.room_id, body.weekday, body.start_time, body.end_time)
    data = body.model_dump()
    # Cot `room` dang chu luon co gia tri de du lieu cu va cho hien thi khong bi trong.
    data["room"] = (data.get("room") or "").strip() or (room.code if room else "")
    sched = models.Schedule(**data)
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return schedule_out(sched)


def update_schedule(db: Session, user: models.User, schedule_id: int,
                    body: schemas.ScheduleUpdate) -> schemas.ScheduleOut:
    sched = _get_or_404(db, schedule_id)
    ensure_class_manage(user, sched.clazz, db)
    data = body.model_dump(exclude_unset=True)
    if "location_id" in data:
        _validate_location(db, data["location_id"])
    room = _validate_room(db, data["room_id"]) if "room_id" in data else None
    start = data.get("start_time", sched.start_time)
    end = data.get("end_time", sched.end_time)
    if start is None or end is None or start >= end:
        raise BadRequestError("Gio bat dau phai truoc gio ket thuc")
    weekday = data.get("weekday", sched.weekday)
    _ensure_room_free(db, data.get("room_id", sched.room_id), weekday, start, end,
                      exclude_id=sched.id)
    if room is not None and not (data.get("room") or "").strip():
        data["room"] = room.code
    for field, value in data.items():
        setattr(sched, field, value)
    if not (sched.room or "").strip():
        raise BadRequestError("Phai chon phong hoc hoac nhap ten phong")
    db.commit()
    db.refresh(sched)
    return schedule_out(sched)


def delete_schedule(db: Session, user: models.User, schedule_id: int) -> dict:
    sched = _get_or_404(db, schedule_id)
    ensure_class_manage(user, sched.clazz, db)
    if schedule_repository.has_sessions(db, schedule_id):
        raise ConflictError("Lich hoc da co phien diem danh, khong the xoa truc tiep")
    db.delete(sched)
    db.commit()
    return {"ok": True}


# ---------------- Tra cuu ----------------

def list_class_schedules(db: Session, user: models.User, class_id: int) -> list[schemas.ScheduleOut]:
    """Lich hoc cua lop: nguoi xem duoc lop, hoac SV dang ghi danh lop do."""
    clazz = class_service.get_or_404(db, class_id)
    allowed = can_view_class(user, clazz, db)
    if not allowed and user.role == ROLE_STUDENT:
        student = student_repository.get_by_user(db, user.id)
        allowed = student is not None and class_repository.is_enrolled(db, class_id, student.id)
    if not allowed:
        raise ForbiddenError("Khong co quyen voi lop hoc phan nay")
    return [schedule_out(s) for s in schedule_repository.of_class(db, class_id)]


def list_all_schedules(db: Session, user: models.User, *, q: str | None, limit: int | None,
                       offset: int) -> Page[schemas.ScheduleWithClassOut]:
    """Lich hoc kem thong tin lop trong pham vi xem cua user (Khoa: lop Khoa quan ly)."""
    page = schedule_repository.search(db, scope=lambda query: filter_classes(query, user, db),
                                      q=q, limit=limit, offset=offset)
    items = [
        schemas.ScheduleWithClassOut(
            id=s.id, class_id=s.class_id, class_code=s.clazz.class_code,
            subject_name=s.clazz.subject_name, weekday=s.weekday,
            start_time=s.start_time, end_time=s.end_time, room=room_label(s),
            room_id=s.room_id,
            location_id=s.location_id, location_name=s.location.name if s.location else None,
        )
        for s in page.items
    ]
    return Page(items, page.total)


def week_schedule(db: Session, user: models.User, start: date | None) -> list[schemas.WeekSlotOut]:
    """Lich hoc/day theo tuan (Thu 2 - CN) cua user dang dang nhap, gop san trang thai phien
    diem danh + ket qua tuong ung (neu co) trong 1 lan goi - tranh client phai goi rieng tung
    buoi (N+1). SV: theo lop da ghi danh. GV: theo lop dang day. Admin/phong ban: theo pham vi
    xem lop (Khoa: lop Khoa quan ly)."""
    base = start or date.today()
    monday = base - timedelta(days=base.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    if user.role == ROLE_STUDENT:
        student = student_repository.get_by_user(db, user.id)
        class_ids = [e.class_id for e in student.enrollments] if student else []
    elif user.role in (ROLE_ADMIN, ROLE_TRAINING, ROLE_AFFAIRS, *FACULTY_ROLES, ROLE_LECTURER):
        class_ids = [c.id for c in class_repository.list_in_scope(
            db, lambda query: filter_classes(query, user, db))]
    else:
        class_ids = []

    if not class_ids:
        return []

    classes_by_id = {c.id: c for c in class_repository.by_ids(db, class_ids)}
    schedules = schedule_repository.of_classes(db, class_ids)
    if not schedules:
        return []

    sessions = session_repository.for_schedules_on(db, [s.id for s in schedules], week_dates)
    session_by_key = {(s.schedule_id, s.session_date): s for s in sessions}
    session_ids = [s.id for s in sessions]

    # SV: trang thai diem danh cua chinh minh cho cac phien trong tuan nay.
    my_status_by_session: dict[int, str] = {}
    if user.role == ROLE_STUDENT and session_ids:
        student = student_repository.get_by_user(db, user.id)
        if student:
            recs = session_repository.records_of_student_in(db, student.id, session_ids)
            my_status_by_session = {r.session_id: r.status for r in recs}

    # Nguoi xem lop (GV/phong ban): so SV co mat khi phien da dong + tong so SV ghi danh lop.
    present_count_by_session: dict[int, int] = {}
    total_count_by_class: dict[int, int] = {}
    if user.role != ROLE_STUDENT:
        closed_ids = [s.id for s in sessions if s.status == "closed"]
        if closed_ids:
            present_count_by_session = session_repository.attended_counts(db, closed_ids)
        total_count_by_class = class_repository.student_counts(db, class_ids)

    fallback_location = default_location(db)
    fallback_fence = (Geofence.from_location(fallback_location)
                      if fallback_location is not None else None)
    result = []
    for d in week_dates:
        weekday = d.weekday()
        for sch in schedules:
            if sch.weekday != weekday:
                continue
            clazz = classes_by_id[sch.class_id]
            session = session_by_key.get((sch.id, d))
            entry = schemas.WeekSlotOut(
                date=d, weekday=weekday, schedule_id=sch.id, class_id=clazz.id,
                class_code=clazz.class_code, subject_name=clazz.subject_name,
                room=room_label(sch), start_time=sch.start_time, end_time=sch.end_time,
                open_from=open_from_time(sch.start_time),
                session_id=session.id if session else None,
                session_status=session.status if session else None,
            )
            fence = resolve_geofence(db, sch, fallback=fallback_fence)
            if fence is not None:
                entry.location_name = fence.name
                entry.location_radius_m = fence.radius_m
            if session:
                entry.my_status = my_status_by_session.get(session.id)
                if session.status == "closed" and user.role != ROLE_STUDENT:
                    entry.present_count = present_count_by_session.get(session.id, 0)
                    entry.total_count = total_count_by_class.get(clazz.id, 0)
            result.append(entry)

    result.sort(key=lambda e: (e.date, e.start_time))
    return result


def today_schedules(db: Session, lecturer: models.Lecturer) -> list[schemas.TodayScheduleOut]:
    """Lich day hom nay cua giang vien, kem phien da mo hom nay (neu co) de client vao thang
    phien thay vi bam mo lai. Quy uoc weekday 0=thu 2 trung voi datetime.weekday()."""
    today: date = datetime.now().date()
    schedules = schedule_repository.of_lecturer_on_weekday(db, lecturer.id, today.weekday())
    sessions = {}
    if schedules:
        sessions = {s.schedule_id: s for s in
                    session_repository.for_schedules_on(db, [s.id for s in schedules], [today])}
    return [
        schemas.TodayScheduleOut(
            schedule_id=s.id, class_id=s.class_id, class_code=s.clazz.class_code,
            subject_name=s.clazz.subject_name, weekday=s.weekday,
            start_time=s.start_time, end_time=s.end_time, room=s.room,
            open_from=open_from_time(s.start_time),
            session_id=sessions[s.id].id if s.id in sessions else None,
            session_status=sessions[s.id].status if s.id in sessions else None,
        )
        for s in schedules
    ]
