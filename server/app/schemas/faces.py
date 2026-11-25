"""Schema Pydantic - nhom faces (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, ConfigDict

from app.core.media import SignedMediaUrl
from app.core.timeutil import LocalDateTime

__all__ = ["EnrollResult", "FacePendingOut", "FaceMineOut", "FaceRejectBody"]


# ---- Face ----
class EnrollResult(BaseModel):
    ok: bool
    message: str
    num_embeddings: int = 0


class FacePendingOut(BaseModel):
    """1 embedding cho duyet, kem anh doi chieu va canh bao trung (neu co)."""
    id: int
    student_id: int
    student_code: str
    full_name: str
    source_image: SignedMediaUrl = ""
    created_at: LocalDateTime
    duplicate_warning: bool = False
    duplicate_student_code: str | None = None
    duplicate_similarity: float | None = None


class FaceMineOut(BaseModel):
    """Du lieu khuon mat cua chinh SV dang dang nhap (khong tra embedding)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    reject_reason: str
    created_at: LocalDateTime
    reviewed_at: LocalDateTime | None = None
    # SV da xac nhan nhan ket qua duyet chua (None: chua xac nhan / chua co ket qua).
    student_ack_at: LocalDateTime | None = None


class FaceRejectBody(BaseModel):
    reason: str
