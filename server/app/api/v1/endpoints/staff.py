"""Controller tai khoan can bo - PH2 (chi quan tri vien)."""
from fastapi import APIRouter, Depends, Response

from app import schemas
from app.api.deps import DbSession, require_roles
from app.db import models
from app.db.models import ROLE_ADMIN
from app.services import staff_service

router = APIRouter(prefix="/staff", tags=["staff"])
AdminOnly = Depends(require_roles(ROLE_ADMIN))


@router.get("", response_model=list[schemas.StaffOut])
def list_staff(response: Response, db: DbSession, q: str | None = None,
               unit_id: int | None = None, limit: int | None = None, offset: int = 0,
               _user: models.User = AdminOnly):
    page = staff_service.list_staff(db, q=q, unit_id=unit_id, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(page.total)
    return page.items


@router.post("", response_model=schemas.StaffOut)
def create_staff(body: schemas.StaffCreate, db: DbSession, _user: models.User = AdminOnly):
    return staff_service.create_staff(db, body)


@router.patch("/{staff_id}", response_model=schemas.StaffOut)
def update_staff(staff_id: int, body: schemas.StaffUpdate, db: DbSession,
                 _user: models.User = AdminOnly):
    return staff_service.update_staff(db, staff_id, body)


@router.delete("/{staff_id}")
def delete_staff(staff_id: int, db: DbSession, _user: models.User = AdminOnly):
    return staff_service.delete_staff(db, staff_id)
