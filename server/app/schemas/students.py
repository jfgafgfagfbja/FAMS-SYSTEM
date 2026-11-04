"""Schema Pydantic - nhom students (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, EmailStr

__all__ = ["StudentCreate", "StudentUpdate", "StudentOut", "ConsentPolicyOut", "ConsentRequest"]


# ---- Student ----
class StudentCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    student_code: str
    major: str = ""
    cohort: int = 0
    faculty_id: int | None = None


class StudentUpdate(BaseModel):
    full_name: str | None = None
    major: str | None = None
    cohort: int | None = None
    faculty_id: int | None = None


class StudentOut(BaseModel):
    id: int
    student_code: str
    full_name: str
    major: str
    cohort: int
    # True khi co it nhat 1 anh khuon mat DA DUOC DUYET (dung duoc de nhan dien).
    face_enrolled: bool = False
    face_status: str = "none"  # none | pending | approved | rejected
    consent_given: bool = False
    consent_version: str | None = None
    consent_method: str | None = None       # self | paper
    consent_recorded_by: str | None = None  # email nguoi ghi nhan
    faculty_id: int | None = None
    faculty_name: str | None = None
    email: str | None = None


# ---- Dong y sinh trac hoc ----
class ConsentPolicyOut(BaseModel):
    version: str
    title: str
    items: list[str]
    checkbox: str


class ConsentRequest(BaseModel):
    """Phai gui dung phien ban noi dung dang hien hanh: SV dong y voi cai da doc."""
    agreed: bool
    version: str
    method: str = "self"  # self: SV tu bam | paper: SV ky giay, can bo nhap thay
