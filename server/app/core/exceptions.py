"""Loi nghiep vu va dinh dang loi thong nhat cua API.

Service va tang phan quyen nem AppError (khong phu thuoc FastAPI/HTTP); handler o day doi
thanh response JSON cung mot dang cho moi loi:

    {"detail": "<thong bao cho nguoi dung>", "code": "<ma may doc>"}

Giu truong "detail" nhu ban goc vi client (Flutter ApiClient) dang doc truong nay. Loi 422
(sai dinh dang du lieu) giu "detail" la danh sach loi tung truong nhu mac dinh cua FastAPI.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Ma loi theo HTTP status, dung khi loi khong tu khai bao code rieng.
CODE_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "too_many_requests",
    500: "internal_error",
    503: "service_unavailable",
}


class AppError(Exception):
    """Loi nghiep vu co the bao cho nguoi dung."""

    status_code = 400

    def __init__(self, detail: str, *, code: str | None = None,
                 headers: dict[str, str] | None = None):
        super().__init__(detail)
        self.detail = detail
        self.code = code or CODE_BY_STATUS.get(self.status_code, "error")
        self.headers = headers


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class TooManyRequestsError(AppError):
    status_code = 429


def error_response(status_code: int, detail, code: str | None = None,
                   headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code or CODE_BY_STATUS.get(status_code, "error")},
        headers=headers,
    )


async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.detail, exc.code, exc.headers)


async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Loi do FastAPI/Starlette tu sinh: thieu token (401), sai duong dan (404), sai method (405)...
    return error_response(exc.status_code, exc.detail, headers=getattr(exc, "headers", None))


async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(422, jsonable_encoder(exc.errors()), "validation_error")


async def _integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    """Luoi an toan: vi pham rang buoc DB chua duoc kiem tra truoc o service (trung khoa,
    khoa ngoai dang duoc tham chieu...) tra 409 thay vi 500."""
    logger.warning("IntegrityError tai %s %s: %s", request.method, request.url.path, exc.orig)
    return error_response(409, "Du lieu bi trung hoac dang duoc su dung o noi khac", "conflict")


async def _rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    response = error_response(429, f"Rate limit exceeded: {exc.detail}", "too_many_requests")
    limiter = getattr(request.app.state, "limiter", None)
    view_limit = getattr(request.state, "view_rate_limit", None)
    if limiter is not None and view_limit is not None:
        response = limiter._inject_headers(response, view_limit)
    return response


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Loi khong luong truoc tai %s %s", request.method, request.url.path)
    return error_response(500, "May chu gap loi, vui long thu lai sau", "internal_error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(IntegrityError, _integrity_error)
    app.add_exception_handler(RateLimitExceeded, _rate_limited)
    app.add_exception_handler(Exception, _unhandled)
