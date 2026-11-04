"""Truy cap bang users va cac bang phu thuoc tai khoan (OTP, refresh token)."""
from sqlalchemy.orm import Session

from app.db import models


def get(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)


def get_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def email_taken(db: Session, email: str) -> bool:
    return get_by_email(db, email) is not None


def has_attendance_edits(db: Session, user_id: int) -> bool:
    """Tai khoan da tung sua ket qua diem danh (attendance_audits.changed_by)."""
    return db.query(models.AttendanceAudit).filter_by(changed_by=user_id).first() is not None


def delete_auth_rows(db: Session, user_id: int) -> None:
    """Xoa du lieu xac thuc phu thuoc user (OTP, refresh token) truoc khi xoa user."""
    db.query(models.PasswordReset).filter_by(user_id=user_id).delete()
    db.query(models.RefreshToken).filter_by(user_id=user_id).delete()


def active_password_resets(db: Session, user_id: int, now_utc) -> list[models.PasswordReset]:
    """Yeu cau dat lai mat khau chua dung va con han."""
    return (
        db.query(models.PasswordReset)
        .filter(models.PasswordReset.user_id == user_id,
                models.PasswordReset.used.is_(False),
                models.PasswordReset.expires_at >= now_utc)
        .all()
    )
