"""Chong lam dung: gioi han tan suat theo IP (slowapi) va dem dang nhap sai theo tai khoan.

Ca hai luu trong bo nho cua tien trinh: chi dung khi chay MOT tien trinh uvicorn (nhu cau hinh
Docker cua du an). Chay nhieu worker can chuyen sang kho dung chung (Redis...).
"""
import time

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)

# Dem so lan dang nhap sai theo tung tai khoan. Bo sung cho gioi han theo IP: SV dung chung
# wifi truong/4G co chung IP, neu chi gioi han theo IP thi ca lop bi khoa; nguoc lai ke do mat
# khau doi IP lien tuc van bi chan theo tai khoan.
_failed_logins: dict[str, list[float]] = {}
_MAX_TRACKED_ACCOUNTS = 10_000


def reset_login_failures() -> None:
    _failed_logins.clear()


def recent_failures(key: str) -> list[float]:
    window = settings.LOGIN_FAILED_WINDOW_MINUTES * 60
    now = time.monotonic()
    attempts = [t for t in _failed_logins.get(key, []) if now - t < window]
    if attempts:
        _failed_logins[key] = attempts
    else:
        _failed_logins.pop(key, None)
    return attempts


def is_locked(key: str) -> bool:
    return len(recent_failures(key)) >= settings.LOGIN_MAX_FAILED_PER_ACCOUNT


def record_failure(key: str) -> None:
    if len(_failed_logins) > _MAX_TRACKED_ACCOUNTS:
        for k in list(_failed_logins):
            recent_failures(k)
    _failed_logins.setdefault(key, []).append(time.monotonic())


def clear_failures(key: str) -> None:
    _failed_logins.pop(key, None)
