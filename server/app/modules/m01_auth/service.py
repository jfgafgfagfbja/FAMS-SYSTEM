"""Nghiep vu xac thuc (PH1): dang nhap, refresh token xoay vong, quen/dat lai/doi mat khau,
dang xuat, thong tin tai khoan."""
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import Request
from sqlalchemy.orm import Session

from app import schemas
from app.core.config import settings
from app.core.consent import CONSENT_VERSION
from app.core.exceptions import BadRequestError, TooManyRequestsError, UnauthorizedError
from app.core.rate_limit import clear_failures, is_locked, record_failure
from app.core.security import (create_access_token, create_refresh_token, hash_password,
                               revoke_all_refresh_tokens, revoke_refresh_token, revoke_token,
                               rotate_refresh_token, verify_password)
from app.db import models
from app.db.models import ROLE_LECTURER, ROLE_STUDENT, STAFF_ROLES
from app.modules.m01_auth import repository as user_repository
from app.repositories import class_repository, lecturer_repository, staff_repository, student_repository
from app.services import audit, email_service
from app.services.mappers import face_status_of

logger = logging.getLogger(__name__)

FORGOT_PASSWORD_MESSAGE = "Neu email ton tai trong he thong, ma OTP da duoc gui den email do."


def _issue_tokens(db: Session, user: models.User) -> schemas.Token:
    return schemas.Token(
        access_token=create_access_token(user.id, user.role, user.token_version), role=user.role,
        refresh_token=create_refresh_token(db, user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _locked_message(prefix: str) -> str:
    return f"{prefix}, vui long thu lai sau {settings.LOGIN_FAILED_WINDOW_MINUTES} phut"


def login(db: Session, request: Request, username: str, password: str) -> schemas.Token:
    """Dang nhap bang email + mat khau. Khoa tam theo tai khoan sau nhieu lan sai (bo sung
    cho gioi han theo IP o controller: nhieu SV dung chung IP wifi truong/4G)."""
    key = username.strip().lower()
    if is_locked(key):
        audit.record_event(db, "auth.login_locked", request=request, email=key, success=False)
        db.commit()
        raise TooManyRequestsError(_locked_message("Dang nhap sai qua nhieu lan"))

    user = user_repository.get_by_email(db, username)
    if not user or not verify_password(password, user.password_hash):
        record_failure(key)
        # Ghi ca email da go (khong ghi mat khau) de phat hien do mat khau theo tai khoan.
        audit.record_event(db, "auth.login_failed", request=request, email=key, success=False)
        db.commit()
        raise UnauthorizedError("Sai email hoac mat khau")

    clear_failures(key)
    audit.record_event(db, "auth.login", request=request, user=user)
    return _issue_tokens(db, user)  # create_refresh_token commit luon dong nhat ky o tren


def refresh(db: Session, refresh_token: str) -> schemas.Token:
    """Doi refresh token lay cap token moi (refresh token cu bi thu hoi - xoay vong)."""
    user, new_refresh = rotate_refresh_token(db, refresh_token)
    return schemas.Token(
        access_token=create_access_token(user.id, user.role, user.token_version), role=user.role,
        refresh_token=new_refresh, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def forgot_password(db: Session, email: str) -> dict:
    """Gui OTP qua email. Luon tra thong bao chung du email co ton tai hay khong (chong do
    email)."""
    generic_response = {"message": FORGOT_PASSWORD_MESSAGE}
    user = user_repository.get_by_email(db, email)
    if not user:
        return generic_response

    otp = f"{secrets.randbelow(1_000_000):06d}"
    db.add(models.PasswordReset(
        user_id=user.id, otp_hash=hash_password(otp),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    ))
    db.commit()

    try:
        email_service.send_otp_email(user.email, otp)
    except Exception:
        # Van tra thong bao chung: tra 500 o day se lo ra email nay CO ton tai.
        logger.exception("Gui email OTP that bai")
    return generic_response


def reset_password(db: Session, body: schemas.ResetPasswordRequest) -> dict:
    """Dat lai mat khau bang OTP: kiem OTP dung + con han + chua dung (so voi TAT CA yeu cau
    con hieu luc, phong truong hop SV xin OTP nhieu lan). Doi xong thu hoi toan bo token dang
    hoat dong cua user qua token_version va refresh token."""
    user = user_repository.get_by_email(db, body.email)
    if not user:
        raise BadRequestError("Thong tin dat lai mat khau khong hop le")

    candidates = user_repository.active_password_resets(db, user.id, datetime.utcnow())
    matched = next((r for r in candidates if verify_password(body.otp, r.otp_hash)), None)
    if not matched:
        raise BadRequestError("Ma OTP khong dung hoac da het han")

    matched.used = True
    _set_password(db, user, body.new_password)
    db.commit()
    return {"ok": True}


def _set_password(db: Session, user: models.User, new_password: str) -> None:
    """Doi mat khau va thu hoi moi phien cu (token_version + refresh token). Chua commit."""
    user.password_hash = hash_password(new_password)
    user.credentials_changed_at = datetime.utcnow()
    user.token_version = (user.token_version or 0) + 1
    revoke_all_refresh_tokens(db, user.id)


def change_password(db: Session, user: models.User,
                    body: schemas.ChangePasswordRequest) -> schemas.Token:
    """Nguoi dang dang nhap tu doi mat khau: phai dung mat khau hien tai (nhap sai nhieu lan
    bi tam khoa giong dang nhap). Doi xong thu hoi moi phien khac va cap token moi cho chinh
    phien nay de nguoi dung khong bi dang xuat giua chung."""
    key = f"change-password:{user.id}"
    if is_locked(key):
        raise TooManyRequestsError(_locked_message("Nhap sai mat khau qua nhieu lan"))

    if not verify_password(body.current_password, user.password_hash):
        record_failure(key)
        raise BadRequestError("Mat khau hien tai khong dung")
    if verify_password(body.new_password, user.password_hash):
        raise BadRequestError("Mat khau moi phai khac mat khau hien tai")

    clear_failures(key)
    _set_password(db, user, body.new_password)
    db.commit()
    db.refresh(user)
    return _issue_tokens(db, user)


def logout(db: Session, request: Request, user: models.User, refresh_token: str | None) -> dict:
    audit.record_event(db, "auth.logout", request=request, user=user)
    revoke_token(db, request.state.token_payload)
    if refresh_token:
        revoke_refresh_token(db, refresh_token, user.id)
    db.commit()
    return {"ok": True}


def _class_brief(c: models.Class) -> schemas.MeClassBrief:
    return schemas.MeClassBrief(id=c.id, class_code=c.class_code, subject_name=c.subject_name,
                                semester=c.semester)


def me(db: Session, user: models.User) -> schemas.MeOut:
    """Thong tin tai khoan dang dang nhap, kem ho so: SV (lop da ghi danh), GV (lop dang
    day), can bo phong ban (don vi) - client dung de dieu huong va hien the ca nhan."""
    data = {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}

    if user.role == ROLE_STUDENT:
        student = student_repository.get_by_user(db, user.id)
        if student:
            data.update(
                student_id=student.id, student_code=student.student_code, major=student.major,
                cohort=student.cohort, consent_given=student.consent_given,
                consent_outdated=(student.consent_given
                                  and student.consent_version != CONSENT_VERSION),
                face_status=face_status_of(student),
                faculty_id=student.faculty_id,
                faculty_name=student.faculty.name if student.faculty else None,
                classes=[_class_brief(e.clazz) for e in student.enrollments],
            )
    elif user.role == ROLE_LECTURER:
        lecturer = lecturer_repository.get_by_user(db, user.id)
        if lecturer:
            data.update(
                lecturer_id=lecturer.id, lecturer_code=lecturer.lecturer_code,
                department=lecturer.department, faculty_id=lecturer.faculty_id,
                faculty_name=lecturer.faculty.name if lecturer.faculty else None,
                classes=[_class_brief(c) for c in class_repository.of_lecturer(db, lecturer.id)],
            )
    elif user.role in STAFF_ROLES:
        staff = staff_repository.get_by_user(db, user.id)
        if staff:
            data.update(
                unit_id=staff.unit_id, unit_code=staff.unit.code, unit_name=staff.unit.name,
                unit_type=staff.unit.type, position=staff.position,
            )

    return schemas.MeOut(**data)
