"""Controller dia diem diem danh - PH2."""
from fastapi import APIRouter, Depends

from app import schemas
from app.api.deps import DbSession, require_roles
from app.core.authz import ACADEMIC_MANAGERS, CLASS_VIEWERS
from app.db import models
from app.services import location_service

router = APIRouter(prefix="/locations", tags=["locations"])
Managers = Depends(require_roles(*ACADEMIC_MANAGERS))


@router.get("", response_model=list[schemas.LocationOut])
def list_locations(db: DbSession, _user: models.User = Depends(require_roles(*CLASS_VIEWERS))):
    return location_service.list_locations(db)


@router.post("", response_model=schemas.LocationOut)
def create_location(body: schemas.LocationCreate, db: DbSession, _user: models.User = Managers):
    return location_service.create_location(db, body)


@router.patch("/{location_id}", response_model=schemas.LocationOut)
def update_location(location_id: int, body: schemas.LocationUpdate, db: DbSession,
                    _user: models.User = Managers):
    return location_service.update_location(db, location_id, body)


@router.delete("/{location_id}")
def delete_location(location_id: int, db: DbSession, _user: models.User = Managers):
    return location_service.delete_location(db, location_id)
