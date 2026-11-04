"""Controller sinh vien, dong y sinh trac, chuyen can 1 SV - PH4/PH8."""
from fastapi import APIRouter, Depends, Response

from app import schemas
from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.authz import STUDENT_MANAGERS
from app.db import models
from app.db.models import FACULTY_ROLES, ROLE_ADMIN, ROLE_AFFAIRS, ROLE_LECTURER, ROLE_TRAINING
from app.services import report_service, student_service

router = APIRouter(prefix="/students", tags=["students"])

STUDENT_LIST_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, ROLE_AFFAIRS, *FACULTY_ROLES, ROLE_LECTURER)
ATTENDANCE_DETAIL_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, ROLE_AFFAIRS, *FACULTY_ROLES)
Managers = Depends(require_roles(*STUDENT_MANAGERS))


@router.post("", response_model=schemas.StudentOut)
def create_student(body: schemas.StudentCreate, db: DbSession, _user: models.User = Managers):
    return student_service.create_student(db, body)


@router.get("", response_model=list[schemas.StudentOut])
def list_students(
    response: Response,
    db: DbSession,
    q: str | None = None,
    faculty_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    user: models.User = Depends(require_roles(*STUDENT_LIST_VIEWERS)),
):
    """Danh sach SV trong pham vi xem cua user, loc theo q (MSSV hoac ho ten)/faculty_id va
    phan trang qua limit/offset. Tong so ban ghi tra qua header X-Total-Count."""
    page = student_service.list_students(db, user, q=q, faculty_id=faculty_id, limit=limit,
                                         offset=offset)
    response.headers["X-Total-Count"] = str(page.total)
    return page.items


# QUAN TRONG: cac duong dan tinh ("/consent-policy", "/me", "/me/attendance") phai khai bao
# TRUOC "/{student_id}" - FastAPI khop route theo thu tu khai bao.
@router.get("/consent-policy", response_model=schemas.ConsentPolicyOut)
def consent_policy_text(_user: CurrentUser):
    return student_service.consent_policy_text()


@router.get("/me", response_model=schemas.StudentOut)
def get_my_student_record(db: DbSession, user: CurrentUser):
    return student_service.get_my_record(db, user)


@router.get("/me/attendance", response_model=list[schemas.MyClassAttendanceOut])
def get_my_attendance(db: DbSession, user: CurrentUser, semester: str | None = None):
    return report_service.my_attendance_detail(db, user, semester)


@router.get("/{student_id}", response_model=schemas.StudentOut)
def get_student(student_id: int, db: DbSession,
                user: models.User = Depends(require_roles(*STUDENT_LIST_VIEWERS))):
    return student_service.get_student(db, user, student_id)


@router.get("/{student_id}/attendance", response_model=list[schemas.MyClassAttendanceOut])
def get_student_attendance(student_id: int, db: DbSession, semester: str | None = None,
                           user: models.User = Depends(require_roles(*ATTENDANCE_DETAIL_VIEWERS))):
    """Phong ban/Khoa xem chuyen can chi tiet 1 SV (vd de duyet don xin phep)."""
    return report_service.student_attendance_for_viewer(db, user, student_id, semester)


@router.patch("/{student_id}", response_model=schemas.StudentOut)
def update_student(student_id: int, body: schemas.StudentUpdate, db: DbSession,
                   _user: models.User = Managers):
    return student_service.update_student(db, student_id, body)


@router.delete("/{student_id}")
def delete_student(student_id: int, db: DbSession, _user: models.User = Managers):
    return student_service.delete_student(db, student_id)


@router.post("/{student_id}/consent")
def give_consent(student_id: int, body: schemas.ConsentRequest, db: DbSession, user: CurrentUser):
    """SV tu xac nhan (method=self) hoac admin/P.CTSV nhap ban giay (method=paper)."""
    return student_service.give_consent(db, user, student_id, body)


@router.post("/{student_id}/consent/withdraw")
def withdraw_student_consent(student_id: int, db: DbSession, user: CurrentUser):
    """Rut dong y: xoa ngay toan bo anh va vector khuon mat."""
    return student_service.withdraw_student_consent(db, user, student_id)
