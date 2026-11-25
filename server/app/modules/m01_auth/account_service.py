"""Nghiep vu dung chung khi tao/xoa tai khoan gan voi ho so (can bo, GV, SV, phu huynh)."""
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError
from app.core.security import hash_password
from app.db import models
from app.modules.m01_auth import repository as user_repository


def ensure_email_available(db: Session, email: str) -> None:
    if user_repository.email_taken(db, email):
        raise BadRequestError("Email da ton tai")


def new_user(db: Session, *, email: str, password: str, role: str, full_name: str) -> models.User:
    """Them user (chua commit) va flush de co id gan vao ho so."""
    user = models.User(email=email, password_hash=hash_password(password), role=role,
                       full_name=full_name)
    db.add(user)
    db.flush()
    return user


def ensure_no_attendance_edits(db: Session, user_id: int) -> None:
    """Tai khoan da tung sua diem danh thi giu lai de doi chieu nhat ky."""
    if user_repository.has_attendance_edits(db, user_id):
        raise ConflictError(
            "Tai khoan da co lich su sua diem danh, khong the xoa (giu lai de doi chieu)")


def delete_profile_and_user(db: Session, profile, user: models.User) -> None:
    """Xoa du lieu xac thuc phu thuoc (OTP, refresh token), ho so (staff/lecturer/student/
    parent) roi den user - dung thu tu cua ban goc. Nguoi goi tu commit."""
    user_repository.delete_auth_rows(db, user.id)
    db.delete(profile)
    db.delete(user)
