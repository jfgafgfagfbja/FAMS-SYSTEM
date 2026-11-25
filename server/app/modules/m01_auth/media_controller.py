"""Controller anh bang chung / anh doi chieu khuon mat qua URL co chu ky HMAC.

URL duoc ky trong response cua cac endpoint da kiem tra quyen (core/media.py), nen dung duoc
ca voi <img src> tren web (khong gui duoc header Authorization) lan Image.network tren Flutter.
"""
from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.modules.m01_auth import media_service

router = APIRouter(tags=["media"])


@router.get("/evidence/{file_path:path}")
def get_media(file_path: str, exp: int = 0, sig: str = ""):
    """Tra anh khi URL co chu ky hop le va con han."""
    full_path = media_service.resolve_signed(file_path, exp, sig)
    return FileResponse(full_path, media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=3000"})
