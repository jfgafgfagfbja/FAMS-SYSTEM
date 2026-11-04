"""Ghi nhan diem danh (PH6): quet camera ca lop, SV tu diem danh (anh + GPS + QR), xac nhan
tay, danh sach ket qua, sua ket qua co ly do va lich su sua.

Nhan dien goi qua ten module face_service.* (test thay the bang monkeypatch).
"""
import os
import uuid
from datetime import datetime, timedelta

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import can_excuse_record, ensure_class_access, ensure_class_view
from app.core.config import settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.db import models
from app.db.models import ROLE_AFFAIRS, ROLE_FACULTY_LEADER
from app.repositories import class_repository, session_repository, student_repository
from app.services import checkin_code_service, face_service
from app.services.geo_service import check_checkin_location, resolve_geofence
from app.services.session_service import _confirm_counts, ensure_accepting_checkins, get_or_404

ALLOWED_EDIT_STATUSES = ("present", "late", "absent", "excused")
# Phe duyet co phep: P.CTSV toan truong, Lanh dao Khoa trong Khoa minh (Van phong Khoa nhap
# lieu, khong phe duyet - xem core/authz.py).
EXCUSE_EDITORS = (ROLE_AFFAIRS, ROLE_FACULTY_LEADER)


def save_evidence(image_bytes: bytes, session_id: int) -> str:
    """Luu frame lam bang chung, tra ve duong dan tho (API ky URL khi tra ve client)."""
    dir_path = os.path.join(settings.EVIDENCE_DIR, str(session_id))
    os.makedirs(dir_path, exist_ok=True)
    filename = f"{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:12]}.jpg"
    with open(os.path.join(dir_path, filename), "wb") as f:
        f.write(image_bytes)
    return f"/evidence/{session_id}/{filename}"


def is_late(session: models.AttendanceSession) -> bool:
    """Dung gio hay muon: so voi gio bat dau tiet + LATE_AFTER_MINUTES."""
    start = datetime.combine(session.session_date, session.schedule.start_time)
    return datetime.now() > start + timedelta(minutes=settings.LATE_AFTER_MINUTES)


# ---------------- Danh sach ----------------

def roster(db: Session, user: models.User, session_id: int) -> list[schemas.RosterEntryOut]:
    """Danh sach SV cua lop gop voi trang thai diem danh cua phien nay trong 1 lan goi."""
    session = get_or_404(db, session_id)
    ensure_class_view(user, session.schedule.class_id, db)
    students = class_repository.students_of_class(db, session.schedule.class_id)
    records = {r.student_id: r for r in session_repository.records_of_session(db, session_id)}

    result = []
    for s in students:
        r = records.get(s.id)
        result.append(schemas.RosterEntryOut(
            student_id=s.id, student_code=s.student_code, full_name=s.user.full_name,
            status=r.status if r else None,
            confidence=r.confidence if r else None,
            evidence_image=r.evidence_image if r else None,
            checked_at=r.checked_at if r else None,
            record_id=r.id if r else None,
            source=r.source if r else None,
            latitude=r.latitude if r else None,
            longitude=r.longitude if r else None,
            location_accuracy=r.location_accuracy if r else None,
            distance_m=r.distance_m if r else None,
        ))
    return result


def list_records(db: Session, user: models.User, session_id: int) -> list[models.AttendanceRecord]:
    session = get_or_404(db, session_id)
    ensure_class_view(user, session.schedule.class_id, db)
    return session_repository.records_of_session(db, session_id)


# ---------------- Quet camera ca lop ----------------

async def recognize(db: Session, user: models.User, session_id: int,
                    frame: UploadFile) -> list[schemas.RecognizeResult]:
    """Nhan 1 frame tu camera lop hoc, nhan dien va tu dong ghi diem danh."""
    session = get_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    ensure_accepting_checkins(session)

    class_id = session.schedule.class_id
    data = await frame.read()
    matches = face_service.recognize_frame(db, data, class_id)

    evidence_path = None
    results = []
    for m in matches:
        is_spoof = m.get("is_spoof", False)
        liveness_score = m.get("liveness_score")
        student = student_repository.get(db, m["student_id"]) if m["student_id"] else None

        if is_spoof:
            # Nghi gia mao: van luu anh bang chung de can bo xem lai ai gian lan,
            # nhung khong ghi attendance record du co nhan ra danh tinh hay khong.
            if evidence_path is None:
                evidence_path = save_evidence(data, session_id)
            results.append(schemas.RecognizeResult(
                student_id=student.id if student else None,
                student_code=student.student_code if student else None,
                full_name=student.user.full_name if student else None,
                confidence=m["confidence"], status="spoof",
                evidence_image=evidence_path, liveness_score=liveness_score,
                bbox=m.get("bbox")))
            continue

        if student is None:
            results.append(schemas.RecognizeResult(
                student_id=None, student_code=None, full_name=None,
                confidence=m["confidence"], status="unknown", evidence_image=None,
                liveness_score=liveness_score, bbox=m.get("bbox")))
            continue

        existed = session_repository.get_record_for(db, session_id, student.id)
        confirm_count = confirm_needed = None
        if existed:
            status = "already_checked"
            evidence = existed.evidence_image
        else:
            # Chi ghi record khi da nhan dien du CONFIRM_FRAMES lan trong phien nay
            # (khong can lien tiep) - giam nhan nham do 1 frame loi thoang qua.
            session_counts = _confirm_counts.setdefault(session_id, {})
            session_counts[student.id] = session_counts.get(student.id, 0) + 1
            confirm_count = session_counts[student.id]
            confirm_needed = settings.CONFIRM_FRAMES

            if confirm_count < confirm_needed:
                results.append(schemas.RecognizeResult(
                    student_id=student.id, student_code=student.student_code,
                    full_name=student.user.full_name,
                    confidence=m["confidence"], status="confirming",
                    evidence_image=None, liveness_score=liveness_score,
                    bbox=m.get("bbox"), confirm_count=confirm_count,
                    confirm_needed=confirm_needed))
                continue

            if evidence_path is None:
                evidence_path = save_evidence(data, session_id)
            db.add(models.AttendanceRecord(
                session_id=session_id, student_id=student.id,
                status="late" if is_late(session) else "present",
                confidence=m["confidence"], evidence_image=evidence_path,
                source="camera"))
            try:
                db.commit()
                status = "recognized"
                evidence = evidence_path
            except IntegrityError:
                # Frame khac (vd 2 thiet bi cung quet) vua ghi record cho SV nay.
                db.rollback()
                status = "already_checked"
                evidence = None

        results.append(schemas.RecognizeResult(
            student_id=student.id, student_code=student.student_code,
            full_name=student.user.full_name,
            confidence=m["confidence"], status=status,
            evidence_image=evidence or None, liveness_score=liveness_score,
            bbox=m.get("bbox"), confirm_count=confirm_count, confirm_needed=confirm_needed))
    return results


# ---------------- Xac nhan tay ----------------

def manual_check(db: Session, user: models.User, session_id: int,
                 body: schemas.ManualCheck) -> models.AttendanceRecord:
    """Giang vien xac nhan tay khi SV khong nhan dien duoc (chi trong phien dang mo,
    chi SV ghi danh lop). Sau khi dong phien, sua trang thai qua PATCH records."""
    session = get_or_404(db, session_id)
    ensure_class_access(user, session.schedule.class_id, db)
    if session.status != "open":
        raise BadRequestError("Phien da dong, hay sua trang thai diem danh thay vi xac nhan tay")

    if not class_repository.is_enrolled(db, session.schedule.class_id, body.student_id):
        raise BadRequestError("Sinh vien khong thuoc lop hoc phan nay")
    if session_repository.get_record_for(db, session_id, body.student_id):
        raise BadRequestError("Sinh vien nay da co record trong phien nay")

    record = models.AttendanceRecord(
        session_id=session_id, student_id=body.student_id, status="manual", source="manual")
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BadRequestError("Sinh vien nay da co record trong phien nay")
    db.refresh(record)
    return record


# ---------------- Sinh vien tu diem danh ----------------

async def self_checkin(db: Session, user: models.User, session_id: int, *, frame: UploadFile,
                       latitude: float | None, longitude: float | None, accuracy: float | None,
                       is_mocked: bool, checkin_code: str | None) -> schemas.SelfCheckinResult:
    """SV tu chup selfie de diem danh: chi nhan dien so voi khuon mat cua CHINH SV dang dang
    nhap (recognize_self). Toa do GPS phai nam trong ban kinh dia diem cua lich hoc (hoac dia
    diem mac dinh) - doi chieu TRUOC khi nhan dien de khong ton tai nguyen. Chi nhan truoc
    han checkin_deadline cua phien."""
    session = get_or_404(db, session_id)
    ensure_accepting_checkins(session)

    student = student_repository.get_by_user(db, user.id)
    if not student:
        raise NotFoundError("Khong tim thay ho so sinh vien")
    if not class_repository.is_enrolled(db, session.schedule.class_id, student.id):
        raise ForbiddenError("Ban khong ghi danh lop hoc phan nay")

    if not student.consent_given:
        return schemas.SelfCheckinResult(
            status="consent_required",
            message="Ban chua dong y su dung du lieu khuon mat. Hay doc va dong y trong muc "
                    "Khuon mat, hoac nho giang vien xac nhan tay.")

    existed = session_repository.get_record_for(db, session_id, student.id)
    if existed:
        return schemas.SelfCheckinResult(
            status="already_checked", record_id=existed.id, record_status=existed.status,
            evidence_image=existed.evidence_image or None, confidence=existed.confidence,
            message="Ban da diem danh phien nay roi")

    if session.require_qr and not checkin_code_service.verify(session.id, checkin_code):
        return schemas.SelfCheckinResult(
            status="qr_required" if not checkin_code else "qr_invalid",
            message=("Buoi nay yeu cau quet ma QR dang chieu trong phong"
                     if not checkin_code
                     else "Ma QR da het han hoac khong dung buoi nay, hay quet lai ma moi nhat"))

    location_check = check_checkin_location(
        resolve_geofence(db, session.schedule), latitude, longitude, accuracy, is_mocked)
    if not location_check.ok:
        return schemas.SelfCheckinResult(
            status=location_check.status, message=location_check.message,
            distance_m=location_check.distance_m, allowed_radius_m=location_check.allowed_radius_m)

    data = await frame.read()
    result = face_service.recognize_self(db, data, student.id)

    if result["status"] == "no_face":
        return schemas.SelfCheckinResult(
            status="no_face", message="Khong tim thay khuon mat trong anh, hay thu lai")
    if result["status"] == "multiple_faces":
        return schemas.SelfCheckinResult(
            status="multiple_faces",
            message="Anh co nhieu hon 1 khuon mat, hay chup rieng minh ban de he thong xac dinh dung danh tinh")
    if result["status"] == "spoof":
        evidence_path = save_evidence(data, session_id)
        return schemas.SelfCheckinResult(
            status="spoof", liveness_score=result["liveness_score"], evidence_image=evidence_path,
            message="Anh nghi la gia mao (anh in/anh chup lai man hinh), vui long chup truc tiep")
    if result["status"] == "not_matched":
        return schemas.SelfCheckinResult(
            status="not_matched", confidence=result["confidence"],
            liveness_score=result["liveness_score"],
            message="Khuon mat khong khop voi du lieu da dang ky cua ban. "
                    "Neu chua dang ky khuon mat, hay vao muc \"Dang ky khuon mat\" truoc.")

    evidence_path = save_evidence(data, session_id)
    record = models.AttendanceRecord(
        session_id=session_id, student_id=student.id,
        status="late" if is_late(session) else "present",
        confidence=result["confidence"], evidence_image=evidence_path,
        source="selfie", latitude=latitude, longitude=longitude, location_accuracy=accuracy,
        distance_m=location_check.distance_m,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        # 2 request tu diem danh gan nhu dong thoi (vd double-click): UNIQUE
        # (session_id, student_id) chan o DB, tra ve record da co thay vi loi 500.
        db.rollback()
        existed = session_repository.get_record_for(db, session_id, student.id)
        return schemas.SelfCheckinResult(
            status="already_checked", record_id=existed.id if existed else None,
            record_status=existed.status if existed else None,
            message="Ban da diem danh phien nay roi")
    db.refresh(record)
    return schemas.SelfCheckinResult(
        status="recognized", confidence=result["confidence"],
        liveness_score=result["liveness_score"], evidence_image=evidence_path,
        record_id=record.id, record_status=record.status,
        message="Diem danh thanh cong",
        distance_m=location_check.distance_m, allowed_radius_m=location_check.allowed_radius_m,
    )


# ---------------- Sua ket qua ----------------

def _record_in_session(db: Session, session_id: int, record_id: int) -> models.AttendanceRecord:
    record = session_repository.get_record(db, record_id)
    if not record or record.session_id != session_id:
        raise NotFoundError("Record khong ton tai trong phien nay")
    return record


def update_record(db: Session, user: models.User, session_id: int, record_id: int,
                  body: schemas.RecordUpdate) -> models.AttendanceRecord:
    """Sua trang thai 1 record (vd SV nop don phep sau buoi hoc). Van sua duoc ke ca khi
    phien da dong, nhung bat buoc phai co ly do - moi lan sua deu luu vao AttendanceAudit.
    GV lop/admin sua moi trang thai; P.CTSV va Lanh dao Khoa (trong pham vi) chi duyet
    "Co phep" (-> excused) hoac huy duyet (excused -> absent)."""
    session = get_or_404(db, session_id)
    record = _record_in_session(db, session_id, record_id)

    if body.status not in ALLOWED_EDIT_STATUSES:
        raise BadRequestError("Trang thai khong hop le")
    if not body.reason.strip():
        raise BadRequestError("Can nhap ly do khi sua diem danh")

    if user.role in EXCUSE_EDITORS:
        if not can_excuse_record(user, record, db):
            raise ForbiddenError("Khong co quyen voi sinh vien/lop hoc phan nay")
        is_excuse = body.status == "excused"
        is_revert = record.status == "excused" and body.status == "absent"
        if not (is_excuse or is_revert):
            raise ForbiddenError("Phong ban chi duoc duyet 'Co phep' hoac huy duyet ve 'Vang'")
    else:
        ensure_class_access(user, session.schedule.class_id, db)

    old_status = record.status
    record.status = body.status
    db.add(models.AttendanceAudit(
        record_id=record.id, changed_by=user.id,
        old_status=old_status, new_status=body.status, reason=body.reason.strip(),
    ))
    db.commit()
    db.refresh(record)
    return record


def record_audits(db: Session, user: models.User, session_id: int,
                  record_id: int) -> list[models.AttendanceAudit]:
    """Lich su sua diem danh cua 1 record (moi nhat truoc)."""
    session = get_or_404(db, session_id)
    ensure_class_view(user, session.schedule.class_id, db)
    _record_in_session(db, session_id, record_id)
    return session_repository.audits_of_record(db, record_id)
