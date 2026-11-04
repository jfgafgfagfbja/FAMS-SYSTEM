"""Schema Pydantic - nhom audit_logs (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, ConfigDict

from app.core.timeutil import LocalDateTime

__all__ = ["AuditLogOut"]


# ---- Nhat ky he thong ----
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: LocalDateTime
    actor_id: int | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    action: str
    target_type: str | None = None
    target_id: int | None = None
    target_label: str | None = None
    ip: str | None = None
    success: bool
    detail: str | None = None  # JSON {truong: [cu, moi]}
