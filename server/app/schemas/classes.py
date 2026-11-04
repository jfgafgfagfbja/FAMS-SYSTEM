"""Schema Pydantic - nhom classes (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, ConfigDict

__all__ = ["ClassCreate", "ClassUpdate", "ClassOut"]


# ---- Class ----
class ClassCreate(BaseModel):
    class_code: str
    subject_name: str
    lecturer_id: int
    semester: str
    faculty_id: int | None = None


class ClassUpdate(BaseModel):
    class_code: str | None = None
    subject_name: str | None = None
    lecturer_id: int | None = None
    semester: str | None = None
    faculty_id: int | None = None


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_code: str
    subject_name: str
    lecturer_id: int
    semester: str
    faculty_id: int | None = None
    lecturer_name: str | None = None
    faculty_name: str | None = None
    student_count: int | None = None
