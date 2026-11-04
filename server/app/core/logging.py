"""Cau hinh log va ma request (request id) cho moi request.

Moi dong log mang [request_id] de lan theo mot request qua nhieu dong log; client gui kem
header X-Request-ID thi dung lai ma do, khong thi server tu sinh. Response luon tra header
X-Request-ID - nguoi dung bao loi kem ma nay la tim duoc dung dong log.
"""
import logging
import re
import time
import uuid
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

LOG_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

access_logger = logging.getLogger("fams.access")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    """Gan dinh dang chung cho log cua ung dung. Goi lai nhieu lan (vd moi lan tao app trong
    test) khong nhan doi handler."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    for handler in root.handlers:
        if getattr(handler, "_fams", False):
            return
    handler = logging.StreamHandler()
    handler._fams = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)


class RequestContextMiddleware:
    """ASGI middleware: gan request id, do thoi gian xu ly va ghi 1 dong log moi request.

    Viet dang ASGI thuan (khong dung BaseHTTPMiddleware) de khong anh huong StreamingResponse
    (xuat Excel) va contextvars.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope.get("headers") or []).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex[:16]
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            payload = (scope.get("state") or {}).get("token_payload") or {}
            access_logger.info(
                "%s %s -> %s %.0fms user=%s", scope.get("method"), scope.get("path"),
                status_holder["status"], elapsed_ms, payload.get("sub", "-"))
            request_id_ctx.reset(token)
