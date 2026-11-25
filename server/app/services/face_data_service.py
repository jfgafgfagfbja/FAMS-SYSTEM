"""Nghiep vu du lieu khuon mat (PH5): quyen dang ky, quy trinh duyet, SV tu quan ly du lieu.

Quy trinh duyet: CHI Phong Cong tac SV duyet hoac tu choi (bat buoc ly do khong hop le) mot anh
dang cho -> he thong gui ket qua cho SV (thong bao) -> SV xac nhan da nhan ket qua.

Phan xu ly anh/nhan dien (InsightFace, chat luong anh, chong gia mao) nam o face_service va
duoc goi qua ten module (face_service.enroll_face) - test thay the ham nay bang monkeypatch.
"""
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app import schemas
from app.core.authz import STUDENT_MANAGERS, can_view_student
from app.core.config import settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.media import delete_media
from app.db import models
from app.db.models import ROLE_LECTURER, ROLE_STUDENT
from app.repositories import face_repository, student_repository
from app.services import face_service, user_notify
from app.services.consent_service import withdraw_consent


def _own_student(db: Session, user: models.User) -> models.Student:
    student = student_repository.get_by_user(db, user.id)
    if not student:
        raise NotFoundError("Khong tim thay ho so sinh vien")
    return student


async def enroll(db: Session, user: models.User, student_id: int,
                 images: list[UploadFile]) -> schemas.EnrollResult:
    """Dang ky khuon mat: moi anh -> 1 embedding trang thai "pending". Duoc thuc hien boi:
    chinh SV, admin/P.CTSV, hoac giang vien voi SV lop minh day. ok=True khi TAT CA anh
    trong lan goi nay dat."""
    student = student_repository.get(db, student_id)
    if not student:
        raise NotFoundError("Sinh vien khong ton tai")
    is_self = user.role == ROLE_STUDENT and student.user_id == user.id
    is_manager = user.role in STUDENT_MANAGERS
    is_own_lecturer = user.role == ROLE_LECTURER and can_view_student(user, student, db)
    if not (is_self or is_manager or is_own_lecturer):
        raise ForbiddenError("Khong co quyen dang ky khuon mat cho sinh vien nay")
    if not student.consent_given:
        raise BadRequestError(
            "Sinh vien chua xac nhan dong y thu thap du lieu khuon mat "
            "(goi POST /students/{id}/consent truoc)")

    ok_count, messages = 0, []
    for img in images:
        data = await img.read()
        try:
            ok, msg = face_service.enroll_face(db, student_id, data)
        except ValueError as e:
            ok, msg = False, str(e)
        if ok:
            ok_count += 1
        messages.append(f"{img.filename}: {msg}")

    all_ok = ok_count == len(images) and ok_count > 0
    return schemas.EnrollResult(ok=all_ok, message="; ".join(messages), num_embeddings=ok_count)


def my_faces(db: Session, user: models.User) -> list[models.FaceEmbedding]:
    """SV xem trang thai cac anh khuon mat da dang ky (kem ly do neu bi tu choi)."""
    return face_repository.of_student(db, _own_student(db, user).id)


def delete_my_faces(db: Session, user: models.User) -> dict:
    """SV tu xoa TOAN BO du lieu khuon mat cua minh va rut lai dong y thu thap - sau do
    khong diem danh bang khuon mat duoc nua cho toi khi dong y + dang ky lai."""
    student = _own_student(db, user)
    deleted = withdraw_consent(db, student)
    db.commit()
    return {"ok": True, "deleted": deleted}


def list_pending(db: Session) -> list[schemas.FacePendingOut]:
    """Embedding cho duyet, kem anh doi chieu va canh bao trung voi SV khac (neu co) - so
    sanh cosine chi voi embedding da duoc duyet."""
    result = []
    for emb in face_repository.pending(db):
        nearest = face_repository.nearest_approved_of_other_student(db, emb)

        duplicate_warning = False
        dup_code = dup_sim = None
        if nearest is not None:
            other_student_id, dist = nearest
            similarity = round(1 - dist, 3)
            if similarity > settings.DUPLICATE_THRESHOLD:
                duplicate_warning = True
                dup_sim = similarity
                other_student = student_repository.get(db, other_student_id)
                dup_code = other_student.student_code if other_student else None

        result.append(schemas.FacePendingOut(
            id=emb.id, student_id=emb.student_id,
            student_code=emb.student.student_code, full_name=emb.student.user.full_name,
            source_image=emb.source_image, created_at=emb.created_at,
            duplicate_warning=duplicate_warning,
            duplicate_student_code=dup_code, duplicate_similarity=dup_sim,
        ))
    return result


def _get_or_404(db: Session, embedding_id: int) -> models.FaceEmbedding:
    emb = face_repository.get(db, embedding_id)
    if not emb:
        raise NotFoundError("Khong tim thay embedding")
    return emb


def _discard_review_image(emb: models.FaceEmbedding) -> None:
    """Anh doi chieu chi phuc vu viec duyet - xoa ngay khi da co quyet dinh."""
    delete_media(emb.source_image)
    emb.source_image = ""


def _decide(db: Session, user: models.User, embedding_id: int, status: str, reason: str) -> models.FaceEmbedding:
    """Ghi quyet dinh cua P.CTSV va gui ket qua cho SV. Chi xu ly anh dang cho duyet."""
    emb = _get_or_404(db, embedding_id)
    if emb.status != "pending":
        raise BadRequestError("Anh khuon mat nay da duoc xu ly truoc do")
    emb.status = status
    emb.reject_reason = reason
    emb.reviewed_by = user.id
    emb.reviewed_at = datetime.now()
    emb.student_ack_at = None
    _discard_review_image(emb)
    if status == "approved":
        user_notify.notify(db, emb.student.user_id, user_notify.KIND_FACE_APPROVED,
                           "Ảnh khuôn mặt đã được duyệt",
                           "Phòng Công tác sinh viên đã duyệt ảnh khuôn mặt của bạn. Từ nay bạn có thể "
                           "điểm danh bằng khuôn mặt. Vui lòng xác nhận đã nhận kết quả trong mục Khuôn mặt.",
                           "/face")
    else:
        user_notify.notify(db, emb.student.user_id, user_notify.KIND_FACE_REJECTED,
                           "Ảnh khuôn mặt không được duyệt",
                           f"Lý do không hợp lệ: {reason}. Hãy chụp lại theo hướng dẫn và xác nhận "
                           "đã nhận kết quả trong mục Khuôn mặt.",
                           "/face")
    db.commit()
    return emb


def approve(db: Session, user: models.User, embedding_id: int) -> dict:
    _decide(db, user, embedding_id, "approved", "")
    return {"ok": True}


def reject(db: Session, user: models.User, embedding_id: int, body: schemas.FaceRejectBody) -> dict:
    reason = body.reason.strip()
    if not reason:
        raise BadRequestError("Can nhap ly do khong hop le khi tu choi")
    _decide(db, user, embedding_id, "rejected", reason)
    return {"ok": True}


def acknowledge(db: Session, user: models.User, embedding_id: int) -> models.FaceEmbedding:
    """SV xac nhan da nhan ket qua duyet (duyet / tu choi) cua mot anh khuon mat cua minh."""
    student = _own_student(db, user)
    emb = face_repository.get(db, embedding_id)
    if emb is None or emb.student_id != student.id:
        raise NotFoundError("Khong tim thay anh khuon mat")
    if emb.status == "pending":
        raise BadRequestError("Anh khuon mat chua co ket qua duyet")
    if emb.student_ack_at is None:
        emb.student_ack_at = datetime.now()
        db.commit()
        db.refresh(emb)
    return emb
