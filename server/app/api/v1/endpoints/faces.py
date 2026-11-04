"""Controller du lieu khuon mat - PH5."""
from fastapi import APIRouter, Depends, File, UploadFile

from app import schemas
from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.authz import STUDENT_MANAGERS
from app.db import models
from app.db.models import ROLE_STUDENT
from app.services import face_data_service

router = APIRouter(prefix="/faces", tags=["faces"])
Managers = Depends(require_roles(*STUDENT_MANAGERS))
StudentOnly = Depends(require_roles(ROLE_STUDENT))


@router.post("/enroll/{student_id}", response_model=schemas.EnrollResult)
async def enroll(student_id: int, db: DbSession, user: CurrentUser,
                 images: list[UploadFile] = File(..., description="1 hoac nhieu anh khuon mat")):
    """Dang ky khuon mat: chinh SV, admin/P.CTSV, hoac GV voi SV lop minh day."""
    return await face_data_service.enroll(db, user, student_id, images)


@router.get("/mine", response_model=list[schemas.FaceMineOut])
def my_faces(db: DbSession, user: models.User = StudentOnly):
    return face_data_service.my_faces(db, user)


@router.delete("/mine")
def delete_my_faces(db: DbSession, user: models.User = StudentOnly):
    return face_data_service.delete_my_faces(db, user)


@router.get("/pending", response_model=list[schemas.FacePendingOut])
def list_pending(db: DbSession, _user: models.User = Managers):
    return face_data_service.list_pending(db)


@router.patch("/{embedding_id}/approve")
def approve_face(embedding_id: int, db: DbSession, _user: models.User = Managers):
    return face_data_service.approve(db, embedding_id)


@router.patch("/{embedding_id}/reject")
def reject_face(embedding_id: int, body: schemas.FaceRejectBody, db: DbSession,
                _user: models.User = Managers):
    return face_data_service.reject(db, embedding_id, body)
