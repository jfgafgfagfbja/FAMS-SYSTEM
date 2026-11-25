"""MOD-01 – Model (M trong MVC): tai khoan nguoi dung, token, yeu cau dat lai mat khau + hang so vai tro."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# Vai tro nguoi dung. Nhom phong ban (TRAINING/AFFAIRS/FACULTY/BOARD) gan voi 1 don vi
# qua bang staff - quyen cu the xem core/authz.py.
ROLE_ADMIN = "admin"
ROLE_LECTURER = "lecturer"
ROLE_STUDENT = "student"
ROLE_PARENT = "parent"
ROLE_TRAINING = "training_office"    # Phong Dao tao
ROLE_AFFAIRS = "student_affairs"     # Phong Cong tac sinh vien
ROLE_FACULTY = "faculty_office"      # Van phong/giao vu Khoa: nhap lieu trong Khoa
ROLE_FACULTY_LEADER = "faculty_leader"  # Lanh dao Khoa (Truong/Pho khoa): giam sat + phe duyet
ROLE_BOARD = "board"                 # Ban nganh khac (chi xem thong ke tong hop)
STAFF_ROLES = (ROLE_TRAINING, ROLE_AFFAIRS, ROLE_FACULTY, ROLE_FACULTY_LEADER, ROLE_BOARD)
# Hai vai tro gan voi mot Khoa (pham vi du lieu = Khoa cua don vi can bo).
FACULTY_ROLES = (ROLE_FACULTY, ROLE_FACULTY_LEADER)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # admin | lecturer | student | parent | training_office | student_affairs | faculty_office | board
    role: Mapped[str] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(255))
    # Moc thoi gian doi mat khau gan nhat (thong tin doi soat; viec thu hoi token dung
    # token_version ben duoi).
    credentials_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Tang len moi lan dat lai mat khau; access token mang claim "tv" - lech version la
    # token cu, bi tu choi ngay (khong phu thuoc do phan giai giay cua "iat").
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")

    student: Mapped["Student | None"] = relationship(back_populates="user")
    lecturer: Mapped["Lecturer | None"] = relationship(back_populates="user")


class RevokedToken(Base):
    """JWT da bi thu hoi (logout truoc han). Kiem tra jti moi lan xac thuc."""
    __tablename__ = "revoked_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class RefreshToken(Base):
    """Refresh token (app mobile). Chi luu SHA-256 cua token; moi lan /auth/refresh xoay
    vong sang token moi, token cu bi thu hoi. Dung lai token da thu hoi = nghi bi danh
    cap -> thu hoi toan bo refresh token cua user."""
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)  # UTC
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # UTC

    user: Mapped[User] = relationship()


class PasswordReset(Base):
    """Yeu cau dat lai mat khau qua OTP gui email. Khong luu OTP tho, chi luu ban bam."""
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    otp_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship()
