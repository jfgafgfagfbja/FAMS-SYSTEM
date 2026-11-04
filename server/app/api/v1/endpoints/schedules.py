"""Controller tra cuu lich hoc va lich tuan - PH3."""
from datetime import date

from fastapi import APIRouter, Depends, Response

from app import schemas
from app.api.deps import CurrentUser, DbSession, require_roles
from app.db import models
from app.db.models import FACULTY_ROLES, ROLE_ADMIN, ROLE_AFFAIRS, ROLE_TRAINING
from app.services import schedule_service

router = APIRouter(prefix="/schedules", tags=["schedules"])

SCHEDULE_LIST_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, ROLE_AFFAIRS, *FACULTY_ROLES)


@router.get("", response_model=list[schemas.ScheduleWithClassOut])
def list_all_schedules(
    response: Response,
    db: DbSession,
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    user: models.User = Depends(require_roles(*SCHEDULE_LIST_VIEWERS)),
):
    """Lich hoc kem thong tin lop trong pham vi xem - loc theo q (ma lop/ten mon/phong),
    phan trang limit/offset, tong so ban ghi o header X-Total-Count."""
    page = schedule_service.list_all_schedules(db, user, q=q, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(page.total)
    return page.items


@router.get("/week", response_model=list[schemas.WeekSlotOut])
def week_schedule(db: DbSession, user: CurrentUser, start: date | None = None):
    """Lich hoc/day theo tuan (Thu 2 - CN) chua ngay `start` (mac dinh hom nay)."""
    return schedule_service.week_schedule(db, user, start)
