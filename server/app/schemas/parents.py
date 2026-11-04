"""Schema Pydantic - nhom parents (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.auth import MeClassBrief
from app.schemas.students import StudentOut

__all__ = ["ParentCreate", "ParentUpdate", "ParentOut", "ParentLinkChild", "ParentChildOut", "ParentPreferencesOut", "ParentPreferencesUpdate"]


# ---- Parent ----
class ParentCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str = ""


class ParentUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None


class ParentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str = ""
    child_count: int = 0


class ParentLinkChild(BaseModel):
    student_code: str


class ParentChildOut(StudentOut):
    """StudentOut mo rong voi danh sach lop hoc phan - dung cho GET /parents/me/children
    de phu huynh co san danh sach hoc ky/lop ma khong phai goi them API khac."""
    classes: list[MeClassBrief] = []


class ParentPreferencesOut(BaseModel):
    notify_email: bool
    notify_present: bool
    # May chu da cau hinh gui email chua - app dung de bao phu huynh khi email chua bat.
    email_available: bool


class ParentPreferencesUpdate(BaseModel):
    notify_email: bool | None = None
    notify_present: bool | None = None
