"""Schema Pydantic - nhom lecturers (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, EmailStr

__all__ = ["LecturerCreate", "LecturerUpdate", "LecturerOut"]


# ---- Lecturer ----
class LecturerCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    lecturer_code: str
    department: str = ""
    faculty_id: int | None = None


class LecturerUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    faculty_id: int | None = None


class LecturerOut(BaseModel):
    id: int
    lecturer_code: str
    full_name: str
    department: str
    email: str | None = None
    faculty_id: int | None = None
    faculty_name: str | None = None
