"""Kiem tra suc khoe dich vu.

- GET /                 : tien trinh con song (giu nhu ban goc; CI va healthcheck container dung).
- GET /api/v1/health    : them kiem tra ket noi CSDL; di qua duoc nginx (/api/...) nen dung de
                          giam sat tu ben ngoai.
"""
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import settings

logger = logging.getLogger(__name__)

root_router = APIRouter(tags=["health"])
router = APIRouter(tags=["health"])


@root_router.get("/")
def root():
    return {"app": "FAMS", "status": "ok"}


@router.get("/health")
def health(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        logger.exception("Kiem tra CSDL that bai")
        database = "error"
    body = {"status": "ok" if database == "ok" else "degraded", "database": database,
            "version": settings.APP_VERSION}
    return JSONResponse(body, status_code=200 if database == "ok" else 503)
