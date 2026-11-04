"""Controller giang vien - PH3."""
from fastapi import APIRouter, Depends, Response

from app import schemas
from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.authz import ACADEMIC_MANAGERS
from app.db import models
from app.db.models import FACULTY_ROLES, ROLE_ADMIN, ROLE_TRAINING
from app.services import lecturer_service, schedule_service

router = APIRouter(prefix="/lecturers", tags=["lecturers"])

LECTURER_LIST_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, *FACULTY_ROLES)
Managers = Depends(require_roles(*ACADEMIC_MANAGERS))


@router.post("", response_model=schemas.LecturerOut)
def create_lecturer(body: schemas.LecturerCreate, db: DbSession, _user: models.User = Managers):
    return lecturer_service.create_lecturer(db, body)


@router.get("", response_model=list[schemas.LecturerOut])
def list_lecturers(
    response: Response,
    db: DbSession,
    q: str | None = None,
    faculty_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    user: models.User = Depends(require_roles(*LECTURER_LIST_VIEWERS)),
):
    """q loc theo ma GV/ho ten, limit/offset phan trang - khong truyen limit thi tra ve toan
    bo. Can bo Khoa chi thay GV thuoc Khoa minh. Tong so ban ghi o header X-Total-Count."""
    page = lecturer_service.list_lecturers(db, user, q=q, faculty_id=faculty_id, limit=limit,
                                           offset=offset)
    response.headers["X-Total-Count"] = str(page.total)
    return page.items


@router.patch("/{lecturer_id}", response_model=schemas.LecturerOut)
def update_lecturer(lecturer_id: int, body: schemas.LecturerUpdate, db: DbSession,
                    _user: models.User = Managers):
    return lecturer_service.update_lecturer(db, lecturer_id, body)


@router.delete("/{lecturer_id}")
def delete_lecturer(lecturer_id: int, db: DbSession, _user: models.User = Managers):
    return lecturer_service.delete_lecturer(db, lecturer_id)


@router.get("/me/today-schedules", response_model=list[schemas.TodayScheduleOut])
def my_today_schedules(db: DbSession, user: CurrentUser):
    """Lich day hom nay cua giang vien dang dang nhap, kem phien da mo hom nay (neu co)."""
    lecturer = lecturer_service.get_own_profile(db, user)
    return schedule_service.today_schedules(db, lecturer)
