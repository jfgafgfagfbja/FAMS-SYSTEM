"""Diem vao cua server FAMS.

Tang lop:  endpoints (controller)  ->  services (nghiep vu)  ->  repositories (truy cap DB)
Moi endpoint nghiep vu nam duoi settings.API_PREFIX (/api/v1); Swagger UI tai /docs.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.m01_auth import health_controller as health
from app.api.v1.router import OPENAPI_TAGS, api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestContextMiddleware, setup_logging
from app.core.rate_limit import limiter
from app.db.database import init_db
from app.jobs.scheduler import start_background_jobs, stop_background_jobs
from app.services import antispoof_service
# Hai module dang ky su kien SQLAlchemy khi duoc import (ghi nhat ky he thong, sinh thong bao
# cho phu huynh). Import tuong minh o day de khong bao gio bi "rung" mat khi sap xep lai code.
from app.services import audit, parent_notify  # noqa: F401

API_DESCRIPTION = """
He thong diem danh sinh vien bang nhan dien khuon mat - Truong Dai hoc Kien truc Da Nang.

* Xac thuc: `POST {prefix}/auth/login` (form `username`, `password`) lay access token, gui kem
  header `Authorization: Bearer <token>`. Nut **Authorize** o tren dung luong nay.
* Loi: `{{"detail": "...", "code": "..."}}`; moi response co header `X-Request-ID`.
* Danh sach co phan trang: tham so `limit`, `offset`; tong so ban ghi o header `X-Total-Count`.
""".format(prefix=settings.API_PREFIX)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    antispoof_service.warm_up()  # log canh bao ngay neu chua co model, thay vi doi request dau
    tasks = start_background_jobs()
    yield
    stop_background_jobs(tasks)


def create_app() -> FastAPI:
    setup_logging(settings.LOG_LEVEL)
    app = FastAPI(
        title="FAMS — Face Attendance Management System",
        version=settings.APP_VERSION,
        description=API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # X-Total-Count: tong so ban ghi cho phan trang; Content-Disposition: ten file Excel;
        # X-Request-ID: ma doi chieu log. Trinh duyet an header tuy chinh neu khong khai bao.
        expose_headers=["X-Total-Count", "Content-Disposition", "X-Request-ID"],
    )
    # Them sau cung = lop ngoai cung: moi response (ke ca loi CORS/500) deu co X-Request-ID.
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health.root_router)
    app.include_router(api_router, prefix=settings.API_PREFIX)
    return app


app = create_app()
