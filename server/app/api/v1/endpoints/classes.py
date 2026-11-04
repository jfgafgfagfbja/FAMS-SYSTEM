"""Controller lop hoc phan, ghi danh, lich hoc cua lop - PH3."""
from fastapi import APIRouter, Depends, Response

from app import schemas
from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.authz import CLASS_EDITORS, CLASS_VIEWERS
from app.db import models
from app.services import class_service, schedule_service

router = APIRouter(prefix="/classes", tags=["classes"])
Editors = Depends(require_roles(*CLASS_EDITORS))


@router.post("", response_model=schemas.ClassOut)
def create_class(body: schemas.ClassCreate, db: DbSession, user: models.User = Editors):
    return class_service.create_class(db, user, body)


@router.get("", response_model=list[schemas.ClassOut])
def list_classes(
    response: Response,
    db: DbSession,
    mine: bool = False,
    q: str | None = None,
    semester: str | None = None,
    faculty_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    user: models.User = Depends(require_roles(*CLASS_VIEWERS)),
):
    """Danh sach lop trong pham vi xem cua user: admin/P.DT/P.CTSV toan truong, Khoa chi
    lop Khoa quan ly, giang vien chi lop minh day (tham so mine giu de tuong thich).
    Loc theo q (ma lop/ten mon), semester, faculty_id; phan trang limit/offset, tong so
    ban ghi tra qua header X-Total-Count."""
    page = class_service.list_classes(db, user, q=q, semester=semester, faculty_id=faculty_id,
                                      limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(page.total)
    return page.items


# ---- Lich hoc cua lop (tao/sua/xoa theo id lich) ----
@router.post("/schedules", response_model=schemas.ScheduleOut)
def create_schedule(body: schemas.ScheduleCreate, db: DbSession, user: models.User = Editors):
    return schedule_service.create_schedule(db, user, body)


@router.patch("/schedules/{schedule_id}", response_model=schemas.ScheduleOut)
def update_schedule(schedule_id: int, body: schemas.ScheduleUpdate, db: DbSession,
                    user: models.User = Editors):
    return schedule_service.update_schedule(db, user, schedule_id, body)


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, db: DbSession, user: models.User = Editors):
    return schedule_service.delete_schedule(db, user, schedule_id)


@router.get("/{class_id}", response_model=schemas.ClassOut)
def get_class(class_id: int, db: DbSession, user: CurrentUser):
    return class_service.get_class(db, user, class_id)


@router.patch("/{class_id}", response_model=schemas.ClassOut)
def update_class(class_id: int, body: schemas.ClassUpdate, db: DbSession,
                 user: models.User = Editors):
    return class_service.update_class(db, user, class_id, body)


@router.delete("/{class_id}")
def delete_class(class_id: int, db: DbSession, user: models.User = Editors):
    return class_service.delete_class(db, user, class_id)


@router.post("/{class_id}/enroll/{student_id}")
def enroll_student(class_id: int, student_id: int, db: DbSession, user: models.User = Editors):
    return class_service.enroll_student(db, user, class_id, student_id)


@router.delete("/{class_id}/enroll/{student_id}")
def unenroll_student(class_id: int, student_id: int, db: DbSession, user: models.User = Editors):
    return class_service.unenroll_student(db, user, class_id, student_id)


@router.get("/{class_id}/students", response_model=list[schemas.StudentOut])
def list_class_students(class_id: int, db: DbSession, user: CurrentUser):
    return class_service.list_class_students(db, user, class_id)


@router.get("/{class_id}/schedules", response_model=list[schemas.ScheduleOut])
def list_class_schedules(class_id: int, db: DbSession, user: CurrentUser):
    """Lich hoc cua lop: nguoi xem duoc lop, hoac SV dang ghi danh lop do."""
    return schedule_service.list_class_schedules(db, user, class_id)
