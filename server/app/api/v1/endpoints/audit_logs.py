"""Controller nhat ky he thong - PH9."""
from datetime import date

from fastapi import APIRouter, Depends, Query, Response

from app import schemas
from app.api.deps import DbSession, require_roles
from app.db import models
from app.db.models import ROLE_ADMIN, ROLE_FACULTY_LEADER
from app.services import audit_log_service

router = APIRouter(prefix="/audit-logs", tags=["audit"])

AUDIT_VIEWERS = (ROLE_ADMIN, ROLE_FACULTY_LEADER)


@router.get("", response_model=list[schemas.AuditLogOut])
def list_audit_logs(
    response: Response,
    db: DbSession,
    q: str | None = Query(default=None, description="Tim theo email nguoi thao tac, doi tuong, hanh dong"),
    action: str | None = Query(default=None, description="Loc theo nhom, vd 'auth.' hoac 'student.'"),
    success: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: models.User = Depends(require_roles(*AUDIT_VIEWERS)),
):
    page = audit_log_service.list_audit_logs(db, user, q=q, action=action, success=success,
                                             date_from=date_from, date_to=date_to, limit=limit,
                                             offset=offset)
    response.headers["X-Total-Count"] = str(page.total)
    return page.items
