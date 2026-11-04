"""Controller hop thu thong bao - PH7."""
from fastapi import APIRouter, Query

from app import schemas
from app.api.deps import CurrentUser, DbSession
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[schemas.NotificationOut])
def list_notifications(db: DbSession, user: CurrentUser, unread_only: bool = False,
                       limit: int = Query(default=50, ge=1, le=200)):
    return notification_service.list_notifications(db, user, unread_only=unread_only, limit=limit)


@router.get("/unread-count", response_model=schemas.UnreadCountOut)
def unread_count(db: DbSession, user: CurrentUser):
    return notification_service.unread_count(db, user)


@router.post("/read-all")
def mark_all_read(db: DbSession, user: CurrentUser):
    return notification_service.mark_all_read(db, user)


@router.post("/{notification_id}/read", response_model=schemas.NotificationOut)
def mark_read(notification_id: int, db: DbSession, user: CurrentUser):
    return notification_service.mark_read(db, user, notification_id)
