"""Kiem tra hop dong Client <-> Server.

Doi chieu MOI endpoint khai bao trong client/lib/api/*.dart voi danh sach route that cua server
(app FastAPI, tien to API_PREFIX). Client goi duong dan/dong tu ma server khong co -> loi.
Endpoint server ma client khong dung -> chi liet ke de tham khao.

Chay (can venv cua server):
    server/venv/Scripts/python scripts/check_api_contract.py      (Windows)
    server/venv/bin/python scripts/check_api_contract.py          (Linux)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from fastapi.routing import APIRoute  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

VERB = {"get": "GET", "getPage": "GET", "getBytes": "GET", "post": "POST",
        "postMultipart": "POST", "patch": "PATCH", "delete": "DELETE"}
CLIENT_CALL = re.compile(r"_c\.(getPage|getBytes|postMultipart|get|post|patch|delete)\(\s*'(/[^']*)'")
# Tang truyen tai (core/api_client.dart) tu goi cac endpoint dang nhap/token bang Dio.
CORE_CALL = re.compile(r"(?:_dio|refreshDio)\.(get|post|patch|delete)(?:<[^(]*>)?\(\s*'(/[^']*)'")
DART_INTERP = re.compile(r"\$\{[^}]+\}|\$[A-Za-z_]\w*")
PATH_PARAM = re.compile(r"\{[^}]+\}")


def server_routes() -> list[tuple[str, str, re.Pattern]]:
    routes = []
    for r in app.routes:
        if not isinstance(r, APIRoute) or not r.path.startswith(settings.API_PREFIX):
            continue
        path = r.path[len(settings.API_PREFIX):]
        pattern = re.compile("^" + PATH_PARAM.sub("[^/]+", re.escape(path).replace(r"\{", "{").replace(r"\}", "}")) + "$")
        for method in r.methods - {"HEAD"}:
            routes.append((method, path, pattern))
    return routes


def client_endpoints() -> list[tuple[str, str, str]]:
    found = []
    for dart in sorted((ROOT / "client" / "lib" / "api").glob("*.dart")):
        for verb, path in CLIENT_CALL.findall(dart.read_text(encoding="utf-8")):
            found.append((VERB[verb], path, dart.name))
    core = ROOT / "client" / "lib" / "core" / "api_client.dart"
    for verb, path in CORE_CALL.findall(core.read_text(encoding="utf-8")):
        found.append((VERB[verb], path, core.name))
    # mediaUrl() ghep duong dan anh /evidence/... (do server tra ve) voi dia chi API.
    found.append(("GET", "/evidence/1", "api_client.dart#mediaUrl"))
    return found


def main() -> int:
    routes = server_routes()
    used = set()
    errors = []
    client = client_endpoints()
    for method, path, source in client:
        sample = DART_INTERP.sub("1", path)
        # Route tinh ("/me", "/schedules"...) phai thang route co tham so - FastAPI cung khop theo
        # thu tu khai bao, nhung o day chi can biet co route nao nhan duoc request nay.
        hits = [(m, p) for m, p, rx in routes if m == method and rx.match(sample)]
        if not hits:
            errors.append(f"  {method} {path}  ({source}) - server KHONG co route nay")
        used.update(hits)
    unused = sorted({(m, p) for m, p, _ in routes} - used, key=lambda x: (x[1], x[0]))

    print(f"Client khai bao {len(client)} endpoint; server co {len(routes)} route duoi {settings.API_PREFIX}.")
    if errors:
        print("LOI - client goi endpoint khong ton tai:")
        print("\n".join(errors))
    else:
        print("OK - moi endpoint client dung deu ton tai tren server (dung dong tu).")
    print(f"Route server client chua dung ({len(unused)}):")
    for m, p in unused:
        print(f"  {m} {p}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
