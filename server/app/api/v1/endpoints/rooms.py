"""Controller phong hoc - PH2."""
from fastapi import APIRouter, Depends, Query

from app import schemas
from app.api.deps import DbSession, require_roles
from app.core.authz import ACADEMIC_MANAGERS, CLASS_VIEWERS
from app.db import models
from app.services import room_service

router = APIRouter(prefix="/rooms", tags=["rooms"])
Viewers = Depends(require_roles(*CLASS_VIEWERS))
Managers = Depends(require_roles(*ACADEMIC_MANAGERS))


@router.get("", response_model=list[schemas.RoomOut])
def list_rooms(
    db: DbSession,
    _user: models.User = Viewers,
    location_id: int | None = None,
    building: str | None = None,
    q: str | None = Query(default=None, description="Tim theo ma hoac ten phong"),
    only_active: bool = True,
):
    return room_service.list_rooms(db, location_id=location_id, building=building, q=q,
                                   only_active=only_active)


@router.get("/buildings", response_model=list[str])
def list_buildings(db: DbSession, _user: models.User = Viewers):
    """Danh sach toa nha dang co - de loc nhanh o man quan ly va o chon phong."""
    return room_service.list_buildings(db)


@router.post("", response_model=schemas.RoomOut)
def create_room(body: schemas.RoomCreate, db: DbSession, _user: models.User = Managers):
    return room_service.create_room(db, body)


@router.patch("/{room_id}", response_model=schemas.RoomOut)
def update_room(room_id: int, body: schemas.RoomUpdate, db: DbSession,
                _user: models.User = Managers):
    return room_service.update_room(db, room_id, body)


@router.delete("/{room_id}")
def delete_room(room_id: int, db: DbSession, _user: models.User = Managers):
    return room_service.delete_room(db, room_id)
