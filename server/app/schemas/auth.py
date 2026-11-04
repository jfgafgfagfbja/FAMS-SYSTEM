"""Schema Pydantic - nhom auth (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, EmailStr, field_validator

__all__ = ["Token", "RefreshRequest", "LogoutRequest", "ForgotPasswordRequest", "ResetPasswordRequest", "ChangePasswordRequest", "MeClassBrief", "MeOut"]


# ---- Auth ----
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    # App mobile luu refresh_token de lay access token moi qua POST /auth/refresh.
    refresh_token: str | None = None
    expires_in: int | None = None  # so giay access token con hieu luc


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    # str thuong, khong dung EmailStr: day la tra cuu email DA TON TAI (giong
    # OAuth2PasswordRequestForm.username o /auth/login), khong phai tao moi, nen
    # khong can/khong nen ep dinh dang - email khong hop le don gian se khong
    # khop user nao va van nhan thong bao chung nhu binh thuong.
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mat khau moi phai co it nhat 8 ky tu")
        return v


class ChangePasswordRequest(BaseModel):
    """Nguoi dang dang nhap tu doi mat khau - bat buoc nhap dung mat khau hien tai."""
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mat khau moi phai co it nhat 8 ky tu")
        return v


# ---- Me ----
class MeClassBrief(BaseModel):
    """Thong tin rut gon 1 lop, dung trong GET /me de frontend lay lich hoc/day."""
    id: int
    class_code: str
    subject_name: str
    semester: str


class MeOut(BaseModel):
    """Thong tin tai khoan dang dang nhap, kem ho so va danh sach lop lien quan."""
    id: int
    email: str
    full_name: str
    role: str
    student_id: int | None = None
    student_code: str | None = None
    major: str | None = None
    cohort: int | None = None
    consent_given: bool | None = None
    # Da dong y nhung voi noi dung phien ban cu -> app nhac doc va xac nhan lai.
    consent_outdated: bool | None = None
    face_status: str | None = None
    lecturer_id: int | None = None
    lecturer_code: str | None = None
    department: str | None = None
    faculty_id: int | None = None
    faculty_name: str | None = None
    # Can bo phong ban
    unit_id: int | None = None
    unit_code: str | None = None
    unit_name: str | None = None
    unit_type: str | None = None
    position: str | None = None
    classes: list[MeClassBrief] = []
