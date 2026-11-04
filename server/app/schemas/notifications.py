"""Schema Pydantic - nhom notifications (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, ConfigDict

from app.core.timeutil import LocalDateTime

__all__ = ["NotificationOut", "UnreadCountOut"]


# ---- Thong bao ----
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    body: str
    link: str | None = None
    created_at: LocalDateTime
    read_at: LocalDateTime | None = None


class UnreadCountOut(BaseModel):
    count: int
