"""Phuc vu anh bang chung qua URL co chu ky (xem core/media.py)."""
import os

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.media import MEDIA_PREFIX, media_file_path, verify_media_signature


def resolve_signed(file_path: str, exp: int, sig: str) -> str:
    """Duong dan file that neu chu ky hop le, con han va khong thoat khoi thu muc anh."""
    if not verify_media_signature(f"{MEDIA_PREFIX}{file_path}", exp, sig):
        raise ForbiddenError("Lien ket anh khong hop le hoac da het han")
    full_path = media_file_path(file_path)
    if not full_path or not os.path.isfile(full_path):
        raise NotFoundError("Khong tim thay anh")
    return full_path
