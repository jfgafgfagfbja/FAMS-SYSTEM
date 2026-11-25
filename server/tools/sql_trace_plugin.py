"""Plugin pytest: ghi lai BANG nao duoc DOC / GHI boi moi endpoint (va moi tac vu nen) khi chay bo test,
tach theo NGUON phat sinh (nghiep vu / xac thuc-phan quyen / trinh nghe thong bao / ghi nhat ky).

Bat moi cau SQL that su gui toi PostgreSQL (su kien before_cursor_execute cua SQLAlchemy), gan voi
request dang xu ly (route template, vd "PATCH /api/v1/sessions/{session_id}/close") hoac tac vu nen
dang chay. Nho vay bat duoc ca phan doc/ghi "ngam": nap quan he lazy, trinh nghe su kien ghi nhat ky
(audit after_flush) va sinh thong bao phu huynh (before_flush) - phan tich tinh khong thay duoc.

Dung (tu thu muc server/):
    PYTHONPATH=tools SQL_TRACE_OUT=../docs/tools/trace/sql_trace.json \
        venv/Scripts/python -m pytest -q -p sql_trace_plugin
Plugin chi QUAN SAT, khong doi ket qua test.
"""
import contextvars
import json
import os
import re
import sys

from fastapi.routing import APIRoute
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Khoa dang xu ly + bo dem {(op, bang)} cua no.
_CURRENT: contextvars.ContextVar = contextvars.ContextVar("sql_trace_current", default=None)
# key -> {"ok": {"R": set, "W": set}, "err": {...}, "status": set, "tests": set}
TRACE: dict[str, dict] = {}

_WRITE_RE = [
    ("W", re.compile(r"^\s*INSERT\s+INTO\s+\"?(\w+)\"?", re.I)),
    ("W", re.compile(r"^\s*UPDATE\s+\"?(\w+)\"?", re.I)),
    ("W", re.compile(r"^\s*DELETE\s+FROM\s+\"?(\w+)\"?", re.I)),
]
_READ_RE = re.compile(r"\b(?:FROM|JOIN)\s+\"?(\w+)\"?", re.I)


def _tables(statement: str) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for op, rx in _WRITE_RE:
        m = rx.match(statement)
        if m:
            found.add((op, m.group(1)))
            # UPDATE ... FROM / DELETE ... USING / INSERT ... SELECT: cac bang con lai la doc
            rest = statement[m.end():]
            found |= {("R", t) for t in _READ_RE.findall(rest)}
            return found
    if re.match(r"^\s*(SELECT|WITH)\b", statement, re.I):
        found |= {("R", t) for t in _READ_RE.findall(statement)}
    return found


# Nguon phat sinh cau SQL, xac dinh bang ngan xep loi goi (khung trong cung khop truoc):
#   auth   - tang xac thuc / phan quyen (app/core/security.py, app/core/authz.py)
#   notify - trinh nghe sinh thong bao phu huynh (app/services/parent_notify.py)
#   audit  - trinh nghe / ham ghi nhat ky (app/services/audit.py)
#   biz    - con lai: nghiep vu cua chinh endpoint / tac vu
_ORIGINS = (("app/core/security.py", "auth"), ("app/core/authz.py", "auth"),
            ("app/services/parent_notify.py", "notify"), ("app/services/audit.py", "audit"))


def _origin() -> str:
    f = sys._getframe(2)
    while f is not None:
        fn = f.f_code.co_filename.replace("\\", "/")
        for suffix, origin in _ORIGINS:
            if fn.endswith(suffix):
                return origin
        f = f.f_back
    return "biz"


@event.listens_for(Engine, "before_cursor_execute")
def _on_sql(conn, cursor, statement, parameters, context, executemany):
    bucket = _CURRENT.get()
    if bucket is not None:
        origin = _origin()
        bucket |= {(op, table, origin) for op, table in _tables(statement)}


def _record(key: str, bucket: set, ok: bool, status=None):
    entry = TRACE.setdefault(key, {"status": set(), "tests": set()})
    for op, table, origin in bucket:
        side = ("ok" if ok else "err") + ("" if origin == "biz" else "_" + origin)
        entry.setdefault(side, {"R": set(), "W": set()})[op].add(table)
    if status is not None:
        entry["status"].add(status)
    test = os.environ.get("PYTEST_CURRENT_TEST", "").split(" ")[0]
    if test:
        entry["tests"].add(test)


# ------------------------------------------------------------------ endpoint
_orig_handle = APIRoute.handle


async def _handle(self, scope, receive, send):
    key = f"{scope['method']} {self.path}"
    bucket: set = set()
    token = _CURRENT.set(bucket)
    status = {"code": None}

    async def _send(message):
        if message.get("type") == "http.response.start":
            status["code"] = message["status"]
        await send(message)

    try:
        return await _orig_handle(self, scope, receive, _send)
    finally:
        _CURRENT.reset(token)
        code = status["code"]
        _record(key, bucket, ok=code is not None and code < 400, status=code)


APIRoute.handle = _handle


# ------------------------------------------------------------------ tac vu nen
def _wrap_job(module, name: str, key: str):
    orig = getattr(module, name)

    def wrapper(*args, **kwargs):
        bucket: set = set()
        token = _CURRENT.set(bucket)
        ok = False
        try:
            result = orig(*args, **kwargs)
            ok = True
            return result
        finally:
            _CURRENT.reset(token)
            _record(key, bucket, ok=ok)

    wrapper.__wrapped__ = orig
    setattr(module, name, wrapper)


def _install_job_wrappers():
    from app.services import evidence_cleanup, parent_notify, session_service

    _wrap_job(session_service, "auto_close_expired_sessions", "JOB auto_close_expired_sessions")
    _wrap_job(evidence_cleanup, "cleanup_expired_evidence", "JOB cleanup_expired_evidence")
    _wrap_job(parent_notify, "send_pending_emails", "JOB send_pending_emails")


def pytest_configure(config):
    # Goi o day (khong phai luc import plugin): luc do pytest da them server/ vao sys.path
    # (pytest.ini: pythonpath = .), va test chua import ham tac vu nen nao.
    _install_job_wrappers()


def pytest_sessionfinish(session, exitstatus):
    out = {}
    for key, e in sorted(TRACE.items()):
        out[key] = {"ok": {"R": [], "W": []}, "err": {"R": [], "W": []},
                    "status": sorted(s for s in e["status"] if s is not None), "tests": sorted(e["tests"])}
        for side, v in e.items():
            if side not in ("status", "tests"):
                out[key][side] = {op: sorted(t) for op, t in v.items()}
    path = os.environ.get("SQL_TRACE_OUT", "sql_trace.json")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
