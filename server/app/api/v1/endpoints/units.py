"""Controller don vi - PH2."""
from fastapi import APIRouter, Depends

from app import schemas
from app.api.deps import DbSession, require_roles
from app.db import models
from app.db.models import (FACULTY_ROLES, ROLE_ADMIN, ROLE_AFFAIRS, ROLE_BOARD, ROLE_LECTURER,
                           ROLE_TRAINING)
from app.services import unit_service

router = APIRouter(prefix="/units", tags=["units"])

# Danh sach don vi dung cho dropdown chon Khoa o cac form va bo loc thong ke.
UNIT_LIST_VIEWERS = (ROLE_ADMIN, ROLE_TRAINING, ROLE_AFFAIRS, *FACULTY_ROLES, ROLE_BOARD,
                     ROLE_LECTURER)


@router.get("", response_model=list[schemas.UnitOut])
def list_units(db: DbSession, type: str | None = None,
               _user: models.User = Depends(require_roles(*UNIT_LIST_VIEWERS))):
    return unit_service.list_units(db, type)


@router.post("", response_model=schemas.UnitOut)
def create_unit(body: schemas.UnitCreate, db: DbSession,
                _user: models.User = Depends(require_roles(ROLE_ADMIN))):
    return unit_service.create_unit(db, body)


@router.patch("/{unit_id}", response_model=schemas.UnitOut)
def update_unit(unit_id: int, body: schemas.UnitUpdate, db: DbSession,
                _user: models.User = Depends(require_roles(ROLE_ADMIN))):
    return unit_service.update_unit(db, unit_id, body)


@router.delete("/{unit_id}")
def delete_unit(unit_id: int, db: DbSession,
                _user: models.User = Depends(require_roles(ROLE_ADMIN))):
    return unit_service.delete_unit(db, unit_id)
