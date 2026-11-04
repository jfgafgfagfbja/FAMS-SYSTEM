"""Plugin pytest: ghi lai (method, route path, status) cua moi request ma bo test goi toi.

Dung: PYTHONPATH=<thu muc nay> ROUTE_COV_OUT=<file.json> pytest -p route_coverage_plugin
"""
import json
import os

from fastapi.routing import APIRoute

HITS: dict[str, set[int]] = {}
_orig_handle = APIRoute.handle


async def _handle(self, scope, receive, send):
    key = f"{scope['method']} {self.path}"

    async def _send(message):
        if message.get("type") == "http.response.start":
            HITS.setdefault(key, set()).add(message["status"])
        await send(message)

    return await _orig_handle(self, scope, receive, _send)


APIRoute.handle = _handle


def pytest_sessionfinish(session, exitstatus):
    from app.main import app

    routes = sorted(
        f"{m} {r.path}" for r in app.routes if isinstance(r, APIRoute) for m in r.methods
        if m != "HEAD"
    )
    out = {
        "routes": routes,
        "hits": {k: sorted(v) for k, v in sorted(HITS.items())},
        "not_hit": [r for r in routes if r not in HITS],
    }
    with open(os.environ.get("ROUTE_COV_OUT", "route_coverage.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
