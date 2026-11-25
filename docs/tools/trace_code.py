"""Truy vet ma nguon FAMS-SYSTEM tu dong (phan tich tinh) -> docs/tools/trace/code_trace.json.

Ket qua dung cho trang "Dac ta chuc nang" va DFD (gen_phan_ra.py):
- moi route: controller, CHUOI GOI controller -> service -> repository (file:dong), loi co the tra ve
  (ma HTTP + thong diep, lay tu cac lenh raise trong chuoi goi), vai tro duoc phep (require_roles),
  tham so / than request / kieu phan hoi (OpenAPI);
- moi tac vu nen: vong lap, chu ky, chuoi goi;
- moi ham trong app/: file, dong, docstring, ham goi toi, loi;
- client Flutter: ham API (verb + duong dan) -> route server; man hinh / widget goi ham do -> duong dan man hinh.

Bang duoc DOC/GHI lay tu chay that (server/tools/sql_trace_plugin.py), khong lay o day.

Chay (tu thu muc goc FAMS-SYSTEM):
    server/venv/Scripts/python docs/tools/trace_code.py
"""
from __future__ import annotations

import ast
import inspect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"
CLIENT = ROOT / "client" / "lib"
OUT = Path(__file__).resolve().parent / "trace" / "code_trace.json"
GITHUB = "https://github.com/jfgafgfagfbja/FAMS-SYSTEM/blob/main/"

sys.path.insert(0, str(SERVER))

from fastapi.routing import APIRoute  # noqa: E402

from app.core import exceptions as exc_mod  # noqa: E402
from app.db.database import Base  # noqa: E402
from app.main import app  # noqa: E402

API_PREFIX = "/api/v1"

# Lop -> ten bang
MODEL_TABLE = {m.class_.__name__: m.class_.__tablename__ for m in Base.registry.mappers}
# Lop loi -> ma HTTP
ERROR_STATUS = {name: obj.status_code for name, obj in vars(exc_mod).items()
                if inspect.isclass(obj) and issubclass(obj, exc_mod.AppError)}
ERROR_STATUS["HTTPException"] = None  # ma lay tu tham so

# Chi di theo cac lop nghiep vu; bo qua schema, cau hinh, log, ket noi DB.
FOLLOW_PREFIXES = ("app.services", "app.repositories", "app.core.authz", "app.core.security",
                   "app.core.rate_limit", "app.jobs")
SKIP_FUNCS = {("app.core.security", "get_current_user")}


def layer_of(mod: str) -> str:
    if mod.startswith("app.api"):
        return "controller"
    if mod.startswith("app.repositories"):
        return "repository"
    if mod.startswith("app.services"):
        return "service"
    if mod.startswith("app.jobs"):
        return "job"
    return "core"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


# ----------------------------------------------------------------------------- chi muc ma server
def module_name(py: Path) -> str:
    parts = list(py.relative_to(SERVER).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def module_file(mod: str) -> Path | None:
    base = SERVER.joinpath(*mod.split("."))
    for cand in (base.with_suffix(".py"), base / "__init__.py"):
        if cand.exists():
            return cand
    return None


MODCONST: dict[str, dict[str, str]] = {}     # mod -> TEN_HANG -> chuoi
INDEX: dict[tuple[str, str], dict] = {}      # (mod, func) -> {node, file, line, doc}
IMPORTS: dict[str, dict[str, tuple]] = {}    # mod -> alias -> ("module", m) | ("name", m, attr)

for py in sorted((SERVER / "app").rglob("*.py")):
    mod = module_name(py)
    tree = ast.parse(py.read_text(encoding="utf-8"))
    imps: dict[str, tuple] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app"):
            for a in node.names:
                alias = a.asname or a.name
                full = f"{node.module}.{a.name}"
                imps[alias] = ("module", full) if module_file(full) else ("name", node.module, a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("app"):
                    imps[a.asname or a.name.split(".")[-1]] = ("module", a.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            INDEX[(mod, node.name)] = {"node": node, "file": py, "line": node.lineno,
                                       "doc": (ast.get_docstring(node) or "").strip()}
    IMPORTS[mod] = imps
    MODCONST[mod] = {t.id: node.value.value for node in tree.body if isinstance(node, ast.Assign)
                     and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
                     for t in node.targets if isinstance(t, ast.Name)}

# Ham "tao loi": return XError(...) - vd authz._forbid; raise _forbid("...") duoc tinh nhu XError("...")
FACTORY: dict[tuple[str, str], tuple[str, str | None]] = {}
for (_m, _f), _info in INDEX.items():
    for _n in ast.walk(_info["node"]):
        if (isinstance(_n, ast.Return) and isinstance(_n.value, ast.Call) and isinstance(_n.value.func, ast.Name)
                and _n.value.func.id in ERROR_STATUS):
            _defaults = _info["node"].args.defaults
            _dflt = None
            if _defaults and isinstance(_defaults[-1], ast.Name):
                _dflt = MODCONST.get(_m, {}).get(_defaults[-1].id)
            elif _defaults and isinstance(_defaults[-1], ast.Constant):
                _dflt = _defaults[-1].value
            FACTORY[(_m, _f)] = (_n.value.func.id, _dflt)


def _msg(node, mod: str | None = None) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and mod and node.id in MODCONST.get(mod, {}):
        return MODCONST[mod][node.id]
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{…}" for v in node.values)
    return "…"


_ANALYSIS: dict[tuple[str, str], dict] = {}


def analyze(mod: str, func: str) -> dict:
    """Ham goi toi (theo thu tu), bang tham chieu tinh, loi raise truc tiep."""
    key = (mod, func)
    if key in _ANALYSIS:
        return _ANALYSIS[key]
    info = INDEX[key]
    imps = IMPORTS.get(mod, {})
    calls: list[tuple[str, str, int]] = []
    models_new: set[str] = set()
    models_ref: set[str] = set()
    errors: list[dict] = []

    def resolve_name(name: str):
        if (mod, name) in INDEX:
            return mod, name
        imp = imps.get(name)
        if imp and imp[0] == "name" and (imp[1], imp[2]) in INDEX:
            return imp[1], imp[2]
        return None

    # Bo qua chu thich kieu (user: models.User, -> models.Class): khong phai doc bang.
    fnode = info["node"]
    ann_nodes = set()
    for a in fnode.args.args + fnode.args.kwonlyargs + fnode.args.posonlyargs +             ([fnode.args.vararg] if fnode.args.vararg else []) + ([fnode.args.kwarg] if fnode.args.kwarg else []):
        if a.annotation is not None:
            ann_nodes |= {id(x) for x in ast.walk(a.annotation)}
    if fnode.returns is not None:
        ann_nodes |= {id(x) for x in ast.walk(fnode.returns)}
    for sub in ast.walk(fnode):
        if isinstance(sub, ast.AnnAssign) and sub.annotation is not None:
            ann_nodes |= {id(x) for x in ast.walk(sub.annotation)}

    for n in ast.walk(info["node"]):
        if id(n) in ann_nodes:
            continue
        if isinstance(n, ast.Call):
            f = n.func
            target = None
            if isinstance(f, ast.Name):
                target = resolve_name(f.id)
                imp = imps.get(f.id)
                if imp and imp[0] == "name" and imp[1] == "app.db.models" and imp[2] in MODEL_TABLE:
                    models_new.add(MODEL_TABLE[imp[2]])
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                imp = imps.get(f.value.id)
                if imp and imp[0] == "module":
                    if (imp[1], f.attr) in INDEX:
                        target = (imp[1], f.attr)
                    elif imp[1] == "app.db.models" and f.attr in MODEL_TABLE:
                        models_new.add(MODEL_TABLE[f.attr])
            if target and target != key:
                calls.append((target[0], target[1], n.lineno))
        elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            imp = imps.get(n.value.id)
            if imp and imp[0] == "module" and imp[1] == "app.db.models" and n.attr in MODEL_TABLE:
                models_ref.add(MODEL_TABLE[n.attr])
        elif isinstance(n, ast.Name):
            imp = imps.get(n.id)
            if imp and imp[0] == "name" and imp[1] == "app.db.models" and imp[2] in MODEL_TABLE:
                models_ref.add(MODEL_TABLE[imp[2]])
        if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and isinstance(n.exc.func, ast.Name):
            cls = n.exc.func.id
            fac = resolve_name(cls)
            if fac and fac in FACTORY:
                fcls, dflt = FACTORY[fac]
                msg = _msg(n.exc.args[0], mod) if n.exc.args else (dflt or "…")
                errors.append({"status": ERROR_STATUS[fcls], "cls": fcls, "msg": msg, "line": n.lineno})
            elif cls in ERROR_STATUS:
                status, message = ERROR_STATUS[cls], "…"
                args = list(n.exc.args)
                kw = {k.arg: k.value for k in n.exc.keywords}
                if cls == "HTTPException":
                    sc = kw.get("status_code") or (args[0] if args else None)
                    status = sc.value if isinstance(sc, ast.Constant) else None
                    if isinstance(sc, ast.Attribute):  # status.HTTP_401_UNAUTHORIZED
                        m = re.search(r"HTTP_(\d{3})", sc.attr)
                        status = int(m.group(1)) if m else None
                    det = kw.get("detail") or (args[1] if len(args) > 1 else None)
                    message = _msg(det) if det is not None else "…"
                else:
                    if args:
                        message = _msg(args[0], mod)
                    elif "detail" in kw:
                        message = _msg(kw["detail"], mod)
                errors.append({"status": status, "cls": cls, "msg": message, "line": n.lineno})

    seen, ordered = set(), []
    for c in calls:
        if (c[0], c[1]) not in seen:
            seen.add((c[0], c[1]))
            ordered.append(c)
    res = {"calls": ordered, "models_new": sorted(models_new), "models_ref": sorted(models_ref),
           "errors": errors}
    _ANALYSIS[key] = res
    return res


def follow(mod: str) -> bool:
    return mod.startswith(FOLLOW_PREFIXES)


def build_chain(mod: str, func: str, depth: int = 0, stack: tuple = ()) -> dict:
    info = INDEX[(mod, func)]
    node = {"fn": f"{mod}.{func}", "layer": layer_of(mod), "file": rel(info["file"]),
            "line": info["line"], "children": []}
    if depth >= 7:
        return node
    for tm, tf, line in analyze(mod, func)["calls"]:
        if not follow(tm) or (tm, tf) in SKIP_FUNCS:
            continue
        if (tm, tf) in stack:
            node["children"].append({"fn": f"{tm}.{tf}", "layer": layer_of(tm), "recursive": True,
                                     "file": rel(INDEX[(tm, tf)]["file"]), "line": INDEX[(tm, tf)]["line"],
                                     "children": []})
            continue
        child = build_chain(tm, tf, depth + 1, stack + ((mod, func),))
        child["call_line"] = line
        node["children"].append(child)
    return node


def collect(chain: dict, acc_err: list, acc_fns: list, acc_models: set):
    mod, func = chain["fn"].rsplit(".", 1)
    acc_fns.append(chain["fn"])
    a = analyze(mod, func)
    for e in a["errors"]:
        acc_err.append({**e, "at": chain["fn"], "file": chain["file"]})
    acc_models.update(a["models_new"])
    for c in chain["children"]:
        if not c.get("recursive"):
            collect(c, acc_err, acc_fns, acc_models)


# ----------------------------------------------------------------------------- quyen theo route
def dependency_info(route: APIRoute) -> dict:
    """Vai tro duoc phep: tim checker do require_roles(...) tao ra trong cay phu thuoc."""
    roles: set[str] = set()
    needs_login = False

    def walk(dep):
        nonlocal needs_login
        call = dep.call
        if call is not None:
            qn = getattr(call, "__qualname__", "")
            if qn.startswith("require_roles"):
                cells = dict(zip(call.__code__.co_freevars, call.__closure__ or ()))
                if "roles" in cells:
                    roles.update(cells["roles"].cell_contents)
            if qn == "get_current_user":
                needs_login = True
        for d in dep.dependencies:
            walk(d)

    walk(route.dependant)
    if roles:
        return {"auth": "roles", "roles": sorted(roles)}
    return {"auth": "login" if needs_login else "public", "roles": []}


# ----------------------------------------------------------------------------- OpenAPI
SPEC = app.openapi()
SCHEMAS = SPEC.get("components", {}).get("schemas", {})


def _type(s: dict) -> str:
    if not s:
        return ""
    if "$ref" in s:
        return s["$ref"].rsplit("/", 1)[-1]
    if "anyOf" in s:
        parts = [_type(x) for x in s["anyOf"] if x.get("type") != "null"]
        return " | ".join(parts) + (" | null" if any(x.get("type") == "null" for x in s["anyOf"]) else "")
    if s.get("type") == "array":
        return f"list[{_type(s.get('items', {}))}]"
    t = s.get("type", "")
    if s.get("format") in ("date", "date-time", "time", "binary", "email"):
        t += f"({s['format']})"
    if "enum" in s:
        t += " " + "/".join(map(str, s["enum"]))
    return t


def _fields(ref_or_schema: dict) -> tuple[str, list[dict]]:
    s = ref_or_schema
    name = ""
    if "$ref" in s:
        name = s["$ref"].rsplit("/", 1)[-1]
        s = SCHEMAS.get(name, {})
    req = set(s.get("required", []))
    return name, [{"name": k, "type": _type(v), "required": k in req,
                   "desc": v.get("description", "")} for k, v in s.get("properties", {}).items()]


def openapi_info(path: str, method: str) -> dict:
    op = SPEC["paths"].get(path, {}).get(method.lower(), {})
    params = [{"name": p["name"], "in": p["in"], "required": p.get("required", False),
               "type": _type(p.get("schema", {}))} for p in op.get("parameters", [])]
    body = None
    if "requestBody" in op:
        for ctype, c in op["requestBody"].get("content", {}).items():
            name, fields = _fields(c.get("schema", {}))
            body = {"content": ctype, "schema": name, "fields": fields}
            break
    resp = ""
    for code in ("200", "201", "204"):
        r = op.get("responses", {}).get(code)
        if r:
            content = r.get("content", {})
            if content:
                ctype, c = next(iter(content.items()))
                resp = _type(c.get("schema", {})) or ctype
                if ctype not in ("application/json",):
                    resp = f"{resp} ({ctype})" if resp != ctype else ctype
            else:
                resp = f"{code} (không có nội dung)"
            break
    return {"summary": op.get("summary", ""), "tag": (op.get("tags") or [""])[0],
            "params": params, "body": body, "response": resp}


# ----------------------------------------------------------------------------- client Flutter
def norm_path(p: str) -> str:
    p = re.sub(r"\$\{[^}]+\}|\$\w+|\{[^}]+\}", "{}", p)
    return p.rstrip("/") or "/"


VERB = {"get": "GET", "getPage": "GET", "getBytes": "GET", "post": "POST", "postMultipart": "POST",
        "patch": "PATCH", "put": "PUT", "delete": "DELETE"}


def client_trace(route_by_norm: dict[tuple[str, str], str]) -> dict:
    files = {p: p.read_text(encoding="utf-8") for p in CLIENT.rglob("*.dart")}
    api_dart = (CLIENT / "api" / "api.dart").read_text(encoding="utf-8")
    getters = dict((g, c + "Api") for c, g in re.findall(r"(\w+)Api get (\w+) => \1Api\(this\);", api_dart))

    methods: dict[str, dict] = {}
    for p, text in files.items():
        if p.parent.name != "api":
            continue
        for cm in re.finditer(r"class (\w+Api) \{(.*?)\n\}", text, re.S):
            cls, body = cm.group(1), cm.group(2)
            getter = next((g for g, c in getters.items() if c == cls), None)
            if not getter:
                continue
            for mm in re.finditer(r"Future<.*?>\s+(\w+)\(([^)]*)\)\s*=>\s*_c\.(\w+)(?:<.*?>)?\(\s*'([^']+)'", body, re.S):
                name, _args, verb, path = mm.groups()
                line = text[:cm.start(2) + mm.start()].count("\n") + 1
                key = (VERB.get(verb, verb.upper()), norm_path(path))
                methods[f"{getter}.{name}"] = {"verb": key[0], "path": path, "route": route_by_norm.get(key),
                                               "file": rel(p), "line": line}
    # Goi truc tiep trong ApiClient (dang nhap, lam moi token, doi mat khau, dang xuat)
    ac = CLIENT / "core" / "api_client.dart"
    ac_text = files[ac]
    for m in re.finditer(r"\.(post|get)<[^(]*>\(\s*'(/auth/[\w-]+)'", ac_text):
        line = ac_text[:m.start()].count("\n") + 1
        before = ac_text[:m.start()]
        fn = re.findall(r"(?:Future<.*?>|void)\s+(_?\w+)\(", before)
        name = fn[-1] if fn else "?"
        key = (m.group(1).upper(), norm_path(m.group(2)))
        methods[f"ApiClient.{name}"] = {"verb": key[0], "path": m.group(2), "route": route_by_norm.get(key),
                                        "file": rel(ac), "line": line}

    # Lop man hinh/widget -> file; router: duong dan -> lop
    class_file: dict[str, Path] = {}
    for p, text in files.items():
        for c in re.findall(r"class (\w+) extends (?:StatelessWidget|StatefulWidget|ConsumerWidget|ChangeNotifier)", text):
            class_file[c] = p
    router = files[CLIENT / "router.dart"]
    screens: dict[Path, list[str]] = {}
    for m in re.finditer(r"path:\s*'([^']+)',\s*builder:\s*\([^)]*\)\s*=>\s*(?:const\s+)?(\w+)\(", router):
        path, cls = m.groups()
        if cls in class_file:
            screens.setdefault(class_file[cls], []).append(path)

    def screens_of(p: Path, depth=0) -> list[str]:
        if p in screens:
            return screens[p]
        if depth > 2:
            return []
        own = [c for c, f in class_file.items() if f == p]
        out: list[str] = []
        for q, text in files.items():
            if q != p and any(re.search(rf"\b{c}\b", text) for c in own):
                out += screens_of(q, depth + 1)
        return sorted(set(out))

    usages: dict[str, list[dict]] = {}
    getter_re = "|".join(map(re.escape, getters))
    for p, text in files.items():
        if p.parent.name == "api":
            continue
        for m in re.finditer(rf"\.({getter_re})\.(\w+)\(", text):
            call = f"{m.group(1)}.{m.group(2)}"
            meth = methods.get(call)
            if not meth or not meth["route"]:
                continue
            usages.setdefault(meth["route"], []).append({
                "call": call, "file": rel(p), "line": text[:m.start()].count("\n") + 1,
                "screens": screens_of(p)})
    # ApiClient.login/... duoc goi qua auth_controller
    for name, meth in methods.items():
        if name.startswith("ApiClient.") and meth["route"]:
            usages.setdefault(meth["route"], []).append({"call": name, "file": meth["file"], "line": meth["line"],
                                                         "screens": []})
    # Anh bang chung khong goi qua lop API: widget EvidenceImage tai thang URL co chu ky.
    ev_route = route_by_norm.get(("GET", "/evidence/{}"))
    if ev_route:
        for p, text in files.items():
            for m in re.finditer(r"\bEvidenceImage\(", text):
                usages.setdefault(ev_route, []).append({
                    "call": "EvidenceImage (URL ký HMAC)", "file": rel(p),
                    "line": text[:m.start()].count("\n") + 1, "screens": screens_of(p)})
    return {"methods": methods, "usages": usages,
            "screens": {rel(p): v for p, v in sorted(screens.items(), key=lambda x: str(x[0]))}}


# ----------------------------------------------------------------------------- main
def main() -> None:
    routes_out: dict[str, dict] = {}
    route_by_norm: dict[tuple[str, str], str] = {}
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        fn = r.endpoint
        mod, func = fn.__module__, fn.__name__
        for method in sorted(r.methods - {"HEAD"}):
            key = f"{method} {r.path}"
            chain = build_chain(mod, func) if (mod, func) in INDEX else {
                "fn": f"{mod}.{func}", "layer": "controller", "file": "", "line": 0, "children": []}
            errs, fns, models_new = [], [], set()
            if (mod, func) in INDEX:
                collect(chain, errs, fns, models_new)
            # loi dung chung cua tang xac thuc / phan quyen
            dep = dependency_info(r)
            if dep["auth"] != "public":
                errs.insert(0, {"status": 401, "cls": "UnauthorizedError", "at": "app.core.security.get_current_user",
                                "msg": "Chưa đăng nhập / token hết hạn hoặc đã thu hồi", "file": "server/app/core/security.py",
                                "line": INDEX[("app.core.security", "get_current_user")]["line"]})
            if dep["auth"] == "roles":
                errs.insert(1, {"status": 403, "cls": "ForbiddenError", "at": "app.core.security.require_roles",
                                "msg": "Khong du quyen", "file": "server/app/core/security.py",
                                "line": INDEX[("app.core.security", "require_roles")]["line"]})
            uniq, seen = [], set()
            for e in errs:
                k = (e["status"], e["msg"])
                if k not in seen:
                    seen.add(k)
                    uniq.append(e)
            routes_out[key] = {
                "method": method, "path": r.path, **dep, **openapi_info(r.path, method),
                "doc": (inspect.getdoc(fn) or "").strip(),
                "endpoint": {"fn": f"{mod}.{func}", "file": chain["file"], "line": chain["line"]},
                "chain": chain, "errors": uniq, "functions": fns, "models_new_static": sorted(models_new),
            }
            route_by_norm[(method, norm_path(r.path[len(API_PREFIX):] if r.path.startswith(API_PREFIX) else r.path))] = key

    jobs = {}
    sched = SERVER / "app" / "jobs" / "scheduler.py"
    sched_text = sched.read_text(encoding="utf-8")
    for jkey, (mod, func, loop) in {
        "JOB auto_close_expired_sessions": ("app.services.session_service", "auto_close_expired_sessions",
                                            "auto_close_sessions_loop"),
        "JOB cleanup_expired_evidence": ("app.services.evidence_cleanup", "cleanup_expired_evidence",
                                         "cleanup_evidence_loop"),
        "JOB send_pending_emails": ("app.services.parent_notify", "send_pending_emails",
                                    "send_notification_emails_loop"),
    }.items():
        chain = build_chain(mod, func)
        errs, fns, models_new = [], [], set()
        collect(chain, errs, fns, models_new)
        loop_line = INDEX[("app.jobs.scheduler", loop)]["line"]
        jobs[jkey] = {"loop": f"app.jobs.scheduler.{loop}", "loop_file": rel(sched), "loop_line": loop_line,
                      "doc": INDEX[(mod, func)]["doc"], "chain": chain, "errors": errs, "functions": fns}

    functions = {}
    for (mod, func), info in INDEX.items():
        if not follow(mod) and not mod.startswith("app.api"):
            continue
        a = analyze(mod, func)
        functions[f"{mod}.{func}"] = {
            "layer": layer_of(mod), "file": rel(info["file"]), "line": info["line"],
            "doc": info["doc"].split("\n\n")[0][:400],
            "calls": [f"{m}.{f}" for m, f, _ in a["calls"] if follow(m) or m.startswith("app.api")],
            "errors": a["errors"], "models_new": a["models_new"], "models_ref": a["models_ref"],
        }

    out = {"github": GITHUB, "api_prefix": API_PREFIX, "models": MODEL_TABLE,
           "routes": routes_out, "jobs": jobs, "functions": functions,
           "client": client_trace(route_by_norm)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # Tom tat + kiem tra
    cl = out["client"]
    unmapped = [k for k, v in cl["methods"].items() if not v["route"]]
    no_client = [k for k in routes_out if k not in cl["usages"]]
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"route: {len(routes_out)} | tac vu nen: {len(jobs)} | ham: {len(functions)}")
    print(f"client: {len(cl['methods'])} ham API, {sum(len(v) for v in cl['usages'].values())} cho goi, "
          f"{len(cl['screens'])} file man hinh co duong dan")
    print(f"ham API client KHONG khop route nao: {unmapped}")
    print(f"route khong co man hinh nao goi ({len(no_client)}): {no_client}")
    print(f"Da ghi {OUT}")


if __name__ == "__main__":
    main()
