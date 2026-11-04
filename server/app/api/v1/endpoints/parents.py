"""Controller phu huynh - PH4 (tai khoan, lien ket), PH7 (tuy chon thong bao), PH8 (xem con)."""
from fastapi import APIRouter, Depends, Response

from app import schemas
from app.api.deps import DbSession, require_roles
from app.core.authz import STUDENT_MANAGERS
from app.db import models
from app.db.models import ROLE_ADMIN, ROLE_AFFAIRS, ROLE_PARENT, ROLE_TRAINING
from app.services import parent_service

router = APIRouter(prefix="/parents", tags=["parents"])

# P.Dao tao duoc xem ho so phu huynh (khong sua) theo ma tran quyen.
PARENT_VIEWERS = (ROLE_ADMIN, ROLE_AFFAIRS, ROLE_TRAINING)
Managers = Depends(require_roles(*STUDENT_MANAGERS))
Viewers = Depends(require_roles(*PARENT_VIEWERS))
ParentOnly = Depends(require_roles(ROLE_PARENT))


# ---- Admin/P.CTSV: quan ly tai khoan phu huynh ----

@router.post("", response_model=schemas.ParentOut)
def create_parent(body: schemas.ParentCreate, db: DbSession, _user: models.User = Managers):
    return parent_service.create_parent(db, body)


@router.get("", response_model=list[schemas.ParentOut])
def list_parents(response: Response, db: DbSession, q: str | None = None,
                 limit: int | None = None, offset: int = 0, _user: models.User = Viewers):
    """Tim theo ten/email, phan trang (X-Total-Count qua header)."""
    page = parent_service.list_parents(db, q=q, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(page.total)
    return page.items


@router.patch("/{parent_id}", response_model=schemas.ParentOut)
def update_parent(parent_id: int, body: schemas.ParentUpdate, db: DbSession,
                  _user: models.User = Managers):
    return parent_service.update_parent(db, parent_id, body)


@router.delete("/{parent_id}")
def delete_parent(parent_id: int, db: DbSession, _user: models.User = Managers):
    return parent_service.delete_parent(db, parent_id)


# ---- Phu huynh: xem con em ----
# QUAN TRONG: cac route "/me/..." phai khai bao TRUOC "/{parent_id}/..." o duoi - FastAPI
# khop route theo THU TU khai bao, de "/{parent_id}/children" truoc thi "/me/children" bi
# "nuot" nham (parent_id="me") va tra ve 422.
@router.get("/me/preferences", response_model=schemas.ParentPreferencesOut)
def my_preferences(db: DbSession, user: models.User = ParentOnly):
    return parent_service.my_preferences(db, user)


@router.patch("/me/preferences", response_model=schemas.ParentPreferencesOut)
def update_my_preferences(body: schemas.ParentPreferencesUpdate, db: DbSession,
                          user: models.User = ParentOnly):
    return parent_service.update_my_preferences(db, user, body)


@router.get("/me/children", response_model=list[schemas.ParentChildOut])
def my_children(db: DbSession, user: models.User = ParentOnly):
    return parent_service.my_children(db, user)


@router.get("/me/children/{student_id}/attendance",
            response_model=list[schemas.MyClassAttendanceOut])
def child_attendance(student_id: int, db: DbSession, semester: str | None = None,
                     user: models.User = ParentOnly):
    return parent_service.child_attendance(db, user, student_id, semester)


# ---- Quan ly lien ket phu huynh <-> sinh vien (dat SAU cac route "/me/...") ----

@router.get("/{parent_id}/children", response_model=list[schemas.StudentOut])
def list_parent_children(parent_id: int, db: DbSession, _user: models.User = Viewers):
    return parent_service.list_children_of(db, parent_id)


@router.post("/{parent_id}/children")
def link_child(parent_id: int, body: schemas.ParentLinkChild, db: DbSession,
               _user: models.User = Managers):
    return parent_service.link_child(db, parent_id, body)


@router.delete("/{parent_id}/children/{student_id}")
def unlink_child(parent_id: int, student_id: int, db: DbSession, _user: models.User = Managers):
    return parent_service.unlink_child(db, parent_id, student_id)
