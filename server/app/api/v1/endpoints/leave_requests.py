"""Controller don xin phep vang - PH6."""
from fastapi import APIRouter, Depends, Query

from app import schemas
from app.api.deps import DbSession, require_roles
from app.core.authz import LEAVE_REVIEWERS, LEAVE_VIEWERS
from app.db import models
from app.db.models import ROLE_STUDENT
from app.services import leave_service

router = APIRouter(prefix="/leave-requests", tags=["leave"])
StudentOnly = Depends(require_roles(ROLE_STUDENT))
Viewers = Depends(require_roles(*LEAVE_VIEWERS))
# Duyet / tu choi: giang vien day lop, Lanh dao Khoa (pham vi kiem tra trong service).
Reviewers = Depends(require_roles(*LEAVE_REVIEWERS))


@router.post("", response_model=schemas.LeaveRequestOut)
def create_leave_request(body: schemas.LeaveRequestCreate, db: DbSession, user: models.User = StudentOnly):
    """SV nop don xin phep vang mot buoi hoc (lich hoc + ngay); giang vien lop nhan thong bao."""
    return leave_service.create(db, user, body)


@router.get("", response_model=list[schemas.LeaveRequestOut])
def list_leave_requests(db: DbSession, status: str | None = None, class_id: int | None = None,
                        limit: int = Query(100, ge=1, le=500), user: models.User = Viewers):
    """SV: don cua minh; GV: lop minh day; Lanh dao Khoa: SV/lop thuoc Khoa; admin, P.CTSV: toan truong."""
    return leave_service.list_requests(db, user, status=status, class_id=class_id, limit=limit)


@router.patch("/{leave_id}/approve", response_model=schemas.LeaveRequestOut)
def approve_leave_request(leave_id: int, body: schemas.LeaveApprove, db: DbSession,
                          user: models.User = Reviewers):
    """Duyet don => buoi do tinh vang co phep; gui ket qua cho SV."""
    return leave_service.approve(db, user, leave_id, body)


@router.patch("/{leave_id}/reject", response_model=schemas.LeaveRequestOut)
def reject_leave_request(leave_id: int, body: schemas.LeaveReject, db: DbSession,
                         user: models.User = Reviewers):
    """Tu choi don kem ly do khong hop le (bat buoc); gui ket qua cho SV."""
    return leave_service.reject(db, user, leave_id, body)


@router.post("/{leave_id}/acknowledge", response_model=schemas.LeaveRequestOut)
def acknowledge_leave_result(leave_id: int, db: DbSession, user: models.User = StudentOnly):
    """SV xac nhan da nhan ket qua duyet don."""
    return leave_service.acknowledge(db, user, leave_id)
