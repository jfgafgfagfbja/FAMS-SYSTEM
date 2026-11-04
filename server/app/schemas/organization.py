"""Schema Pydantic - nhom organization (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.db.models import ROLE_BY_UNIT_TYPE

__all__ = ["UnitCreate", "UnitUpdate", "UnitOut", "StaffCreate", "StaffUpdate", "StaffOut"]


# ---- Don vi (Khoa/Phong/Ban) ----
class UnitCreate(BaseModel):
    code: str
    name: str
    type: str  # faculty | training | student_affairs | board

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in ROLE_BY_UNIT_TYPE:
            raise ValueError("Loai don vi phai la faculty, training, student_affairs hoac board")
        return v


class UnitUpdate(BaseModel):
    code: str | None = None
    name: str | None = None


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    type: str


# ---- Can bo phong ban ----
class StaffCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    unit_id: int
    position: str = ""
    # Chi co nghia voi don vi loai Khoa: True = Lanh dao Khoa (Truong/Pho khoa, giam sat +
    # phe duyet), False = Van phong Khoa (giao vu, nhap lieu).
    faculty_leader: bool = False

    @field_validator("password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mat khau phai co it nhat 8 ky tu")
        return v


class StaffUpdate(BaseModel):
    full_name: str | None = None
    unit_id: int | None = None
    position: str | None = None
    faculty_leader: bool | None = None


class StaffOut(BaseModel):
    id: int
    user_id: int
    email: str
    full_name: str
    role: str
    unit_id: int
    unit_code: str
    unit_name: str
    unit_type: str
    position: str
