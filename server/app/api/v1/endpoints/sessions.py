"""Controller phien diem danh va ket qua diem danh - PH6."""
from fastapi import APIRouter, Depends, File, Form, UploadFile

from app import schemas
from app.api.deps import DbSession, require_roles
from app.core.authz import CLASS_VIEWERS
from app.db import models
from app.db.models import ROLE_ADMIN, ROLE_LECTURER, ROLE_STUDENT
from app.services import attendance_service, session_service
from app.services.attendance_service import EXCUSE_EDITORS

router = APIRouter(prefix="/sessions", tags=["attendance"])

Operators = Depends(require_roles(ROLE_LECTURER, ROLE_ADMIN))   # GV lop minh / admin
Viewers = Depends(require_roles(*CLASS_VIEWERS))
StudentOnly = Depends(require_roles(ROLE_STUDENT))


# ---------------- Phien ----------------

@router.post("", response_model=schemas.SessionOut)
def open_session(body: schemas.SessionCreate, db: DbSession, user: models.User = Operators):
    """Mo phien: dung ngay hom nay, dung thu cua lich, trong khung
    [gio bat dau - EARLY_OPEN_MINUTES, gio ket thuc], moi lich toi da 1 phien/ngay."""
    return session_service.open_session(db, user, body)


@router.get("", response_model=list[schemas.SessionDetail])
def list_sessions(db: DbSession, status: str | None = None, class_id: int | None = None,
                  mine: bool = False, limit: int | None = None, user: models.User = Viewers):
    """Phien trong pham vi xem lop cua user, loc theo status (open/closed) va class_id.
    Tham so mine giu de tuong thich - pham vi da duoc gioi han theo vai tro."""
    return session_service.list_sessions(db, user, status=status, class_id=class_id, limit=limit)


@router.get("/{session_id}", response_model=schemas.SessionDetail)
def get_session(session_id: int, db: DbSession, user: models.User = Viewers):
    return session_service.get_session(db, user, session_id)


@router.patch("/{session_id}", response_model=schemas.SessionDetail)
def update_session(session_id: int, body: schemas.SessionUpdate, db: DbSession,
                   user: models.User = Operators):
    """Bat/tat yeu cau quet ma QR cho buoi dang dien ra."""
    return session_service.update_session(db, user, session_id, body)


@router.get("/{session_id}/checkin-info", response_model=schemas.CheckinInfoOut)
def checkin_info(session_id: int, db: DbSession, user: models.User = StudentOnly):
    return session_service.checkin_info(db, user, session_id)


@router.get("/{session_id}/checkin-code", response_model=schemas.CheckinCodeOut)
def session_checkin_code(session_id: int, db: DbSession, user: models.User = Viewers):
    """Ma QR dang hieu luc de giang vien chieu trong phong (chi nguoi day/quan ly lop)."""
    return session_service.checkin_code(db, user, session_id)


@router.get("/{session_id}/roster", response_model=list[schemas.RosterEntryOut])
def session_roster(session_id: int, db: DbSession, user: models.User = Viewers):
    """Danh sach SV cua lop gop voi trang thai diem danh cua phien nay."""
    return attendance_service.roster(db, user, session_id)


@router.patch("/{session_id}/close")
def close_session(session_id: int, db: DbSession, user: models.User = Operators):
    """Dong phien: SV chua co record -> absent; tra kem SV vua vuot nguong canh bao."""
    return session_service.close_session_by_user(db, user, session_id)


# ---------------- Ghi nhan diem danh ----------------

@router.post("/{session_id}/recognize", response_model=list[schemas.RecognizeResult])
async def recognize(session_id: int, db: DbSession, frame: UploadFile = File(...),
                    user: models.User = Operators):
    """Nhan 1 frame tu camera lop hoc, nhan dien va tu dong ghi diem danh."""
    return await attendance_service.recognize(db, user, session_id, frame)


@router.post("/{session_id}/manual", response_model=schemas.RecordOut)
def manual_check(session_id: int, body: schemas.ManualCheck, db: DbSession,
                 user: models.User = Operators):
    return attendance_service.manual_check(db, user, session_id, body)


@router.post("/{session_id}/self-checkin", response_model=schemas.SelfCheckinResult)
async def self_checkin(
    session_id: int,
    db: DbSession,
    frame: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    accuracy: float | None = Form(None),
    is_mocked: bool = Form(False),
    checkin_code: str | None = Form(None),
    user: models.User = StudentOnly,
):
    """SV tu diem danh: anh tu chup + GPS (+ ma QR neu buoi hoc yeu cau)."""
    return await attendance_service.self_checkin(
        db, user, session_id, frame=frame, latitude=latitude, longitude=longitude,
        accuracy=accuracy, is_mocked=is_mocked, checkin_code=checkin_code)


@router.get("/{session_id}/records", response_model=list[schemas.RecordOut])
def list_records(session_id: int, db: DbSession, user: models.User = Viewers):
    return attendance_service.list_records(db, user, session_id)


@router.patch("/{session_id}/records/{record_id}", response_model=schemas.RecordOut)
def update_record(session_id: int, record_id: int, body: schemas.RecordUpdate, db: DbSession,
                  user: models.User = Depends(require_roles(ROLE_LECTURER, ROLE_ADMIN,
                                                            *EXCUSE_EDITORS))):
    """Sua trang thai (bat buoc ly do, luu lich su). Phong ban chi duyet/huy "Co phep"."""
    return attendance_service.update_record(db, user, session_id, record_id, body)


@router.get("/{session_id}/records/{record_id}/audits",
            response_model=list[schemas.AttendanceAuditOut])
def list_record_audits(session_id: int, record_id: int, db: DbSession,
                       user: models.User = Viewers):
    """Lich su sua diem danh cua 1 record."""
    return attendance_service.record_audits(db, user, session_id, record_id)
