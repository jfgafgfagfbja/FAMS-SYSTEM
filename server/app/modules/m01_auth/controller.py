"""Controller xac thuc - PH1. Gioi han tan suat theo IP (slowapi) dat o day vi slowapi gan
vao ham endpoint; khoa tam theo tai khoan nam trong auth_service."""
from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app import schemas
from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.rate_limit import limiter
from app.modules.m01_auth import service as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.Token)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
def login(request: Request, db: DbSession, form: OAuth2PasswordRequestForm = Depends()):
    """Form `username` (email), `password`. Tra access token + refresh token + vai tro."""
    return auth_service.login(db, request, form.username, form.password)


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("60/minute")
def refresh(request: Request, body: schemas.RefreshRequest, db: DbSession):
    """Doi refresh token lay cap token moi (token cu bi thu hoi - xoay vong)."""
    return auth_service.refresh(db, body.refresh_token)


@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(request: Request, body: schemas.ForgotPasswordRequest, db: DbSession):
    """Gui ma OTP qua email; luon tra thong bao chung (khong lo email ton tai hay khong)."""
    return auth_service.forgot_password(db, body.email)


@router.post("/reset-password")
@limiter.limit("10/hour")
def reset_password(request: Request, body: schemas.ResetPasswordRequest, db: DbSession):
    """Dat lai mat khau bang OTP; moi token cu mat hieu luc."""
    return auth_service.reset_password(db, body)


@router.post("/change-password", response_model=schemas.Token)
@limiter.limit("10/minute")
def change_password(request: Request, body: schemas.ChangePasswordRequest, db: DbSession,
                    user: CurrentUser):
    """Doi mat khau (phai dung mat khau hien tai); cap token moi cho phien hien tai."""
    return auth_service.change_password(db, user, body)


@router.post("/logout")
def logout(request: Request, db: DbSession, user: CurrentUser,
           body: schemas.LogoutRequest | None = None):
    return auth_service.logout(db, request, user, body.refresh_token if body else None)


@router.get("/me", response_model=schemas.MeOut)
def get_me(db: DbSession, user: CurrentUser):
    """Thong tin tai khoan dang dang nhap kem ho so theo vai tro."""
    return auth_service.me(db, user)
