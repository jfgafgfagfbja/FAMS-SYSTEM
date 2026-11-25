"""Sinh PHAN RA CHUC NANG + DFD CAC MUC + DAC TA & TRUY VET cua FAMS -> docs/so-do-luong-du-lieu-va-csdl/.

    server/venv/Scripts/python docs/tools/gen_phan_ra.py [--png | --png-all]

Dau vao:
- docs/tools/phan_ra_data.py      : phan ra (phan he -> chuc nang cap 2 -> la) + dac ta nghiep vu tung la
- docs/tools/feature_inventory.py : 126 tinh nang (ma, tac nhan, endpoint, man hinh, test)
- docs/tools/trace/code_trace.json: chuoi goi, loi, vai tro, tham so, man hinh client (trace_code.py)
- docs/tools/trace/sql_trace.json : bang doc/ghi khi chay that 279 test (server/tools/sql_trace_plugin.py)
Dau ra:
- phan_ra_chuc_nang.html (+ phan_ra_chuc_nang.svg/.png) : so do phan ra chuc nang (BFD) den chuc nang la
- dfd.html (+ dfd/*.svg, dfd/*.png)                    : DFD ngu canh, muc 0, muc 1, muc 2 (ky hieu giao trinh PTTK)
- dac_ta_chuc_nang.html                                 : dac ta + truy vet tung chuc nang la, ma tran truy vet
- trace/leaf_index.json : de gen_so_do_csdl.py gan lien ket vao 4 trang cu (goi tu dong o cuoi)

Nguyen tac: luong du lieu chi khai bao o MUC LA; muc tren duoc GOP tu muc duoi => cac muc luon can bang.
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
import textwrap
from collections import OrderedDict
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))

import feature_inventory as FI  # noqa: E402
import phan_ra_data as P  # noqa: E402
from so_do_data import FLOWS, PROJECT, ROLES, STORES, TABLES  # noqa: E402

OUT = ROOT / "docs" / "so-do-luong-du-lieu-va-csdl"
TRACE = TOOLS / "trace"
CODE = json.loads((TRACE / "code_trace.json").read_text(encoding="utf-8"))
SQL = json.loads((TRACE / "sql_trace.json").read_text(encoding="utf-8"))
GH = CODE["github"]
esc = html.escape


def nkey(s: str):
    return tuple(int(x) if x.isdigit() else x for x in re.split(r"[.\-]", s))


# ============================================================================ mo hinh
FEATS: dict[str, dict] = {}
for ph_code, _t, feats in FI.PHAN_HE:
    for fid, name, actor, ref, screen, ev, change in feats:
        FEATS[fid] = dict(name=name, actor=actor, ref=ref, screen=screen, evidence=ev, change=change, ph=ph_code)

ENT_NAME = {c: n for c, n, _r, _g in P.ENTITIES}
ENT_GROUP = {c: g for c, _n, _r, g in P.ENTITIES}
ENT_ROLES = {c: r for c, _n, r, _g in P.ENTITIES}
CTX_NAME = dict(P.CONTEXT_ENTITIES)
ROLE2ENT = {r: c for c, _n, roles, _g in P.ENTITIES for r in roles}
ALL_ROLES = [r for _c, _n, roles, _g in P.ENTITIES for r in roles]
STORE_NAME = {c: n for c, n, _t in STORES + P.EXTRA_STORES}
STORE_TABLES = {c: t for c, _n, t in STORES + P.EXTRA_STORES}
TABLE_STORE = {t: c for c, _n, tabs in STORES for t in tabs}
TABLE_TITLE = {t: d["title"] for t, d in TABLES.items()}
ROLE_VN = {r["role"]: r["name"] for r in ROLES}
ROLE_ID = {r["role"]: r["id"] for r in ROLES}
JOB_OF = {"run_auto_close_loop": "JOB auto_close_expired_sessions",
          "run_notification_email_loop": "JOB send_pending_emails",
          "run_cleanup_loop": "JOB cleanup_expired_evidence"}
PH_COLORS = ["#2563EB", "#0891B2", "#059669", "#7C3AED", "#DB2777", "#EA580C", "#D97706", "#0E9594", "#475569", "#64748B"]

PHS, GROUPS, LEAVES, BY_FID, BY_ID = [], {}, [], {}, {}
for idx, (ph, n, ph_name, groups) in enumerate(P.PHAN_RA):
    PHS.append({"code": ph, "n": n, "name": ph_name, "groups": [g[0] for g in groups], "color": PH_COLORS[idx],
                "dfd": ph not in P.NO_DFD})
    for gid, gname, fids in groups:
        GROUPS[gid] = {"id": gid, "name": gname, "ph": ph, "leaves": []}
        for i, fid in enumerate(fids, 1):
            lid = f"{gid}.{i}"
            leaf = {"id": lid, "fid": fid, "ph": ph, "group": gid, "name": FEATS[fid]["name"], **P.LEAF[fid]}
            LEAVES.append(leaf)
            BY_FID[fid] = leaf
            BY_ID[lid] = leaf
            GROUPS[gid]["leaves"].append(lid)
PH_BY_CODE = {p["code"]: p for p in PHS}


def resolve_refs(leaf) -> list[str]:
    raw = leaf.get("refs")
    if raw is None:
        t = FEATS[leaf["fid"]]["ref"]
        m = re.match(r"(GET|POST|PATCH|PUT|DELETE) (\S+)", t)
        if m:
            cands = [f"{m.group(1)} {CODE['api_prefix']}{m.group(2)}", f"{m.group(1)} {m.group(2)}"]
            hit = [c for c in cands if c in CODE["routes"]]
            if not hit:
                raise SystemExit(f"{leaf['fid']}: khong thay route {t}")
            raw = [hit[0]]
        elif t.startswith("nền: "):
            raw = [JOB_OF[t.split(": ", 1)[1]]]
        else:
            raise SystemExit(f"{leaf['fid']}: tham chieu '{t}' can khai bao refs trong phan_ra_data.py")
    return raw


def business_tables(route_key: str) -> set[str]:
    tabs = set()
    for fn in CODE["routes"][route_key]["functions"]:
        if fn.startswith(("app.core.authz", "app.core.security")):
            continue
        f = CODE["functions"].get(fn)
        if f:
            tabs |= set(f["models_ref"]) | set(f["models_new"])
    return tabs


def listener_reads(module: str) -> set[str]:
    out = set()
    for k, f in CODE["functions"].items():
        if k.startswith(module + "."):
            out |= set(f["models_ref"])
    return out


# Trinh nghe thong bao doc lien ket phu huynh qua quan he ORM (phan tich tinh khong thay) -> khai bao them.
LISTENER_READS = {"notifications": (listener_reads("app.services.parent_notify") | {"parents", "parent_students"})
                  - {"notifications"},
                  "audit_logs": listener_reads("app.services.audit") - {"audit_logs"},
                  "attendance_audits": set()}
OWNERS = {fid for fid, _l in P.REDIRECT.values()} | {fid for fid, _l in P.REDIRECT_BY_SOURCE.values()}

for leaf in LEAVES:
    refs = resolve_refs(leaf)
    leaf["routes"] = [r for r in refs if r in CODE["routes"]]
    leaf["jobs"] = [r for r in refs if r.startswith("JOB ")]
    leaf["fns"] = [r[3:] for r in refs if r.startswith("FN ")]
    leaf["files"] = [r[5:] for r in refs if r.startswith("FILE ")]
    leaf["kind"] = ("api" if leaf["routes"] else "job" if leaf["jobs"] else
                    "client" if any(f.startswith("client/") for f in leaf["files"]) else "internal")
    # tac nhan
    if "ent" in leaf:
        ents = list(leaf["ent"])
    else:
        ents = []
        for rk in leaf["routes"]:
            r = CODE["routes"][rk]
            ents += [ROLE2ENT[x] for x in r["roles"]] if r["auth"] == "roles" else ["ND"]
    order = [c for c, *_ in P.ENTITIES]
    leaf["ents"] = sorted(set(ents), key=order.index)
    # vai tro he thong duoc dung chuc nang (cho cay chuc nang theo vai tro)
    roles = set()
    for rk in leaf["routes"]:
        r = CODE["routes"][rk]
        if r["auth"] == "roles" and "ent" not in leaf:
            roles |= set(r["roles"])
    if not roles:
        for e in leaf["ents"]:
            roles |= set(ALL_ROLES) if e == "ND" else set(ENT_ROLES.get(e, []))
    leaf["roles"] = [r for r in ALL_ROLES if r in roles]
    leaf["readonly"] = bool(leaf["routes"]) and all(r.startswith("GET ") for r in leaf["routes"])
    # bang doc / ghi: chay that + khai bao them
    R, W = set(), set()
    for key in leaf["routes"] + leaf["jobs"]:
        s = SQL.get(key)
        if not s:
            continue
        # Doc: chi phan NGHIEP VU (plugin tach theo ngan xep loi goi); voi PH1 doc cho xac thuc cung la nghiep vu.
        R |= set(s["ok"]["R"])
        if leaf["ph"] == "PH1":
            R |= set(s.get("ok_auth", {}).get("R", []))
        # Ghi: moi nguon (ghi cua trinh nghe se duoc doi thanh luong toi tien trinh phu trach ben duoi).
        for side in ("ok", "ok_auth", "ok_notify", "ok_audit"):
            W |= set(s.get(side, {}).get("W", []))
    extra_store = {"R": set(), "W": set()}
    for mode, tb in leaf.get("kho", []):
        for m in mode:
            if tb in ("M1", "F1"):
                extra_store[m].add(tb)
            else:
                (R if m == "R" else W).add(tb)
    leaf["redirects"] = []
    for tb in sorted(W):
        if tb in P.REDIRECT:
            explicit = P.REDIRECT_BY_SOURCE.get((tb, leaf["fid"]))
            owner, label = explicit or P.REDIRECT[tb]
            # Khai bao rieng (REDIRECT_BY_SOURCE) thi luon doi luong; con lai chi doi khi KHAC phan he voi tien
            # trinh phu trach (vd 7.2.3 danh dau da doc ghi notifications cung PH7 => ghi kho truc tiep).
            if owner != leaf["fid"] and (explicit or leaf["ph"] != FEATS[owner]["ph"]):
                W.discard(tb)
                kind = "audit" if tb in ("audit_logs",) else "event"
                leaf["redirects"].append((owner, label, kind, tb))
    # Quy tac nghiep vu (BUSINESS_LOGIC muc 9): MOI lan tao / doi trang thai ban ghi diem danh deu kich hoat
    # sinh thong bao phu huynh (7.1.1) - ke ca khi bo test khong co phu huynh lien ket nen khong do duoc.
    # (Chi PH6 tao / doi trang thai ban ghi; 9.3.1 don anh chi xoa duong dan anh - khong sinh thong bao.)
    if ("attendance_records" in W and leaf["ph"] == "PH6"
            and not any(o == "7.01" for o, *_ in leaf["redirects"])):
        leaf["redirects"].append(("7.01", P.REDIRECT["notifications"][1], "event", "notifications"))
    leaf["R"], leaf["W"] = sorted(R - W), sorted(W)
    leaf["RW"] = sorted(R & W)
    leaf["R"] = sorted(R - set(leaf["RW"]))
    leaf["W"] = sorted(W - set(leaf["RW"]))
    stores = {"R": set(extra_store["R"]), "W": set(extra_store["W"])}
    for tb in R:
        if tb in TABLE_STORE:
            stores["R"].add(TABLE_STORE[tb])
    for tb in W:
        if tb in TABLE_STORE:
            stores["W"].add(TABLE_STORE[tb])
    leaf["stores"] = stores


# ----------------------------------------------------------------------------- luong muc la
def E(c): return ("E", c)
def Pn(f): return ("P", f)
def S(c): return ("S", c)


FLOWS_LEAF: list[dict] = []


def add_flow(s, d, label, kind, origin):
    FLOWS_LEAF.append({"s": s, "d": d, "label": label, "kind": kind, "origin": origin})


for leaf in LEAVES:
    if leaf["ph"] in P.NO_DFD:
        continue
    fid = leaf["fid"]
    for e in leaf["ents"]:
        if leaf.get("vao"):
            add_flow(E(e), Pn(fid), leaf["vao"], "data", fid)
        if leaf.get("ra"):
            add_flow(Pn(fid), E(e), leaf["ra"], "data", fid)
    for direction, e, label in leaf.get("ext", []):
        add_flow(Pn(fid), E(e), label, "data", fid) if direction == "->" else add_flow(E(e), Pn(fid), label, "data", fid)
    for st in sorted(leaf["stores"]["R"]):
        add_flow(S(st), Pn(fid), "", "read", fid)
    for st in sorted(leaf["stores"]["W"]):
        add_flow(Pn(fid), S(st), "", "write", fid)
    for direction, other, label in leaf.get("p2p", []):
        add_flow(Pn(fid), Pn(other), label, "data", fid) if direction == "->" else add_flow(Pn(other), Pn(fid), label, "data", fid)
    for owner, label, kind, _tb in leaf["redirects"]:
        add_flow(Pn(fid), Pn(owner), label, kind, fid)
# bo trung
_seen, _uniq = set(), []
for f in FLOWS_LEAF:
    k = (f["s"], f["d"], f["label"], f["kind"])
    if k not in _seen:
        _seen.add(k)
        _uniq.append(f)
FLOWS_LEAF = _uniq


# ============================================================================ so do DFD
def proc_name(pid: str) -> tuple[str, str]:
    """(so hieu hien thi, ten) cua tien trinh o moi muc."""
    if pid == "0":
        return "0", PROJECT["short"] + " — " + "Hệ thống điểm danh khuôn mặt"
    if pid in PH_BY_CODE:
        return str(PH_BY_CODE[pid]["n"]), PH_BY_CODE[pid]["name"]
    if pid in GROUPS:
        return pid, GROUPS[pid]["name"]
    leaf = BY_ID[pid]
    return pid, leaf["name"]


def diagram_href(pid: str) -> str:
    if pid == "0":
        return "#L0"
    if pid in PH_BY_CODE:
        return f"#L1-{pid}" if PH_BY_CODE[pid]["dfd"] else ""
    if pid in GROUPS:
        g = GROUPS[pid]
        if len(g["leaves"]) > 1 and PH_BY_CODE[g["ph"]]["dfd"]:
            return f"#L2-{pid}"
        return f"dac_ta_chuc_nang.html#{g['leaves'][0]}"
    return f"dac_ta_chuc_nang.html#{pid}"


DIAGRAMS: "OrderedDict[str, dict]" = OrderedDict()


def make_diagram(did, level, title, parent_proc, mapper, internal):
    edges: "OrderedDict[tuple, dict]" = OrderedDict()
    for f in FLOWS_LEAF:
        s2, d2 = mapper(f["s"]), mapper(f["d"])
        if s2 is None or d2 is None or s2 == d2:
            continue
        if not (s2 in internal or d2 in internal):
            continue
        e = edges.setdefault((s2, d2), {"s": s2, "d": d2, "labels": [], "kinds": set(), "origins": []})
        if f["label"] and f["label"] not in e["labels"]:
            e["labels"].append(f["label"])
        e["kinds"].add(f["kind"])
        if f["origin"] not in e["origins"]:
            e["origins"].append(f["origin"])
    nodes = set(internal)
    for (s2, d2) in edges:
        nodes.add(s2)
        nodes.add(d2)
    DIAGRAMS[did] = {"id": did, "level": level, "title": title, "parent": parent_proc,
                     "internal": internal, "nodes": nodes, "edges": list(edges.values())}


def leaf_of(fid): return BY_FID[fid]


# Ngu canh
make_diagram("CTX", -1, "Sơ đồ ngữ cảnh (mức khung cảnh)", None,
             lambda n: ("P", "0") if n[0] == "P" else (("E", ENT_GROUP[n[1]]) if n[0] == "E" else None),
             [("P", "0")])
# Muc 0
DFD_PHS = [p for p in PHS if p["dfd"]]
make_diagram("L0", 0, "DFD mức 0 (mức đỉnh)", "0",
             lambda n: ("P", leaf_of(n[1])["ph"]) if n[0] == "P" else (("E", ENT_GROUP[n[1]]) if n[0] == "E" else n),
             [("P", p["code"]) for p in DFD_PHS])
# Muc 1
for p in DFD_PHS:
    def m1(n, code=p["code"]):
        if n[0] == "P":
            lf = leaf_of(n[1])
            return ("P", lf["group"]) if lf["ph"] == code else ("X", lf["ph"])
        return n
    make_diagram(f"L1-{p['code']}", 1, f"DFD mức 1 — tiến trình {p['n']}. {p['name']}", p["code"], m1,
                 [("P", g) for g in p["groups"]])
# Muc 2
for p in DFD_PHS:
    for gid in p["groups"]:
        g = GROUPS[gid]
        if len(g["leaves"]) < 2:
            continue

        def m2(n, gid=gid):
            if n[0] == "P":
                lf = leaf_of(n[1])
                return ("P", lf["id"]) if lf["group"] == gid else ("X", lf["id"])
            return n
        make_diagram(f"L2-{gid}", 2, f"DFD mức 2 — tiến trình {gid}. {g['name']}", gid, m2,
                     [("P", lid) for lid in g["leaves"]])


# ----------------------------------------------------------------------------- kiem tra can bang
def up_map(node, level_parent: int):
    """Anh xa nut cua so do con len muc cha (de so sanh luong ngoai)."""
    kind, v = node
    if kind == "E":
        return ("E", ENT_GROUP[v]) if level_parent <= 0 else node
    if kind in ("P", "X"):
        if level_parent == 0:   # cha la muc 0: so do con la muc 1
            if v in GROUPS:
                return ("P", GROUPS[v]["ph"])
            return ("P", v) if v in PH_BY_CODE else ("P", BY_ID[v]["ph"])
        if level_parent == 1:   # cha la muc 1: so do con la muc 2
            if v in BY_ID:
                return ("P", BY_ID[v]["group"]) if BY_ID[v]["ph"] == BY_ID[v]["ph"] else ("P", BY_ID[v]["ph"])
            return ("P", v)
    return node


def interface(did: str, proc_node, level_parent: int, from_child: bool):
    d = DIAGRAMS[did]
    out = set()
    for e in d["edges"]:
        s, t = e["s"], e["d"]
        if from_child:
            s, t = up_map(s, level_parent), up_map(t, level_parent)
            inside = lambda n: n == proc_node  # noqa: E731
        else:
            inside = lambda n: n == proc_node  # noqa: E731
        if inside(s) and not inside(t):
            for lb in e["labels"] or [""]:
                out.add(("->", t, lb, "store" if t[0] == "S" else "x"))
        elif inside(t) and not inside(s):
            for lb in e["labels"] or [""]:
                out.add(("<-", s, lb, "store" if s[0] == "S" else "x"))
    return out


def fix_level1_up(node):
    """Nut cua so do muc 2 len muc 1 (nut ngoai la la thuoc phan he khac -> ten phan he)."""
    kind, v = node
    if kind in ("P", "X") and v in BY_ID:
        lf = BY_ID[v]
        return lf["group"], lf["ph"]
    return None


BALANCE = {}
for p in DFD_PHS:
    parent_if = {x for x in interface("L0", ("P", p["code"]), 0, False) if x[1][0] != "S" or True}
    child_if = interface(f"L1-{p['code']}", ("P", p["code"]), 0, True)
    # o muc 0 kho la nut ngoai; o muc 1 kho cung la nut ngoai -> so sanh truc tiep
    BALANCE[f"L1-{p['code']}"] = (parent_if == child_if, len(parent_if), sorted(map(str, parent_if ^ child_if))[:6])
for did, d in DIAGRAMS.items():
    if d["level"] != 2:
        continue
    gid = d["parent"]
    ph = GROUPS[gid]["ph"]
    # luong ngoai cua tien trinh gid trong so do muc 1
    par = set()
    for e in DIAGRAMS[f"L1-{ph}"]["edges"]:
        if e["s"] == ("P", gid) and e["d"] != ("P", gid):
            par |= {("->", e["d"], lb) for lb in (e["labels"] or [""])}
        if e["d"] == ("P", gid) and e["s"] != ("P", gid):
            par |= {("<-", e["s"], lb) for lb in (e["labels"] or [""])}
    chi = set()

    def up1(n, ph=ph):
        if n[0] in ("P", "X") and n[1] in BY_ID:
            lf = BY_ID[n[1]]
            return ("P", lf["group"]) if lf["ph"] == ph else ("X", lf["ph"])
        return n
    for e in d["edges"]:
        s, t = up1(e["s"]), up1(e["d"])
        if s == ("P", gid) and t != ("P", gid):
            chi |= {("->", t, lb) for lb in (e["labels"] or [""])}
        if t == ("P", gid) and s != ("P", gid):
            chi |= {("<-", s, lb) for lb in (e["labels"] or [""])}
    BALANCE[did] = (par == chi, len(par), sorted(map(str, par ^ chi))[:6])
# ngu canh <-> muc 0
ctx_if = {("->" if e["s"] == ("P", "0") else "<-", e["d"] if e["s"] == ("P", "0") else e["s"], lb)
          for e in DIAGRAMS["CTX"]["edges"] for lb in (e["labels"] or [""])}
l0_if = set()
for e in DIAGRAMS["L0"]["edges"]:
    if e["s"][0] == "P" and e["d"][0] == "E":
        l0_if |= {("->", e["d"], lb) for lb in e["labels"] or [""]}
    if e["d"][0] == "P" and e["s"][0] == "E":
        l0_if |= {("<-", e["s"], lb) for lb in e["labels"] or [""]}
BALANCE["L0"] = (ctx_if == l0_if, len(ctx_if), sorted(map(str, ctx_if ^ l0_if))[:6])


# ============================================================================ ve SVG
R_PROC, EW, EH, SW, SH = 60, 178, 52, 240, 42
CSS_SVG = """
text{font-family:'Segoe UI',Arial,sans-serif;fill:#1f2937}
.pc{fill:#fff7ed;stroke:#ea580c;stroke-width:2.2}.px{fill:#f8fafc;stroke:#94a3b8;stroke-width:1.6;stroke-dasharray:6 4}
.pid{font-size:13px;font-weight:800;fill:#9a3412}.pxid{font-size:12px;font-weight:700;fill:#64748b}
.pn{font-size:10.6px}.en{fill:#e0f2fe;stroke:#0369a1;stroke-width:1.8}.et{font-size:11.5px;font-weight:600;fill:#0c4a6e}
.sl{stroke:#0f766e;stroke-width:2}.sc{fill:#ccfbf1;stroke:#0f766e;stroke-width:2}.sid{font-size:12px;font-weight:800;fill:#0f766e}
.st{font-size:11px;fill:#134e4a}.e{fill:none;stroke-width:1.5}.k-data{stroke:#334155}.k-read{stroke:#2563eb}
.k-write{stroke:#ea580c}.k-rw{stroke:#7c3aed}.k-event{stroke:#db2777;stroke-dasharray:5 3}
.k-audit{stroke:#94a3b8;stroke-dasharray:4 3}.lb{font-size:10.4px;paint-order:stroke;stroke:#fff;stroke-width:3.2px;
stroke-linejoin:round}.lb-audit{fill:#64748b}.lb-event{fill:#9d174d}.ttl{font-size:16px;font-weight:800;fill:#0f2a3d}
.sub{font-size:11.5px;fill:#64748b}.lg{font-size:10.5px;fill:#334155}a{cursor:pointer}a:hover .pc,a:hover .en{filter:brightness(.96)}
"""
MARKERS = "".join(
    f'<marker id="m-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
    for k, c in [("data", "#334155"), ("read", "#2563eb"), ("write", "#ea580c"), ("rw", "#7c3aed"),
                 ("event", "#db2777"), ("audit", "#94a3b8")])


def wrap(text: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(text, width) or [""]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(0, width - 1)].rstrip() + "…"
    return lines


def label_lines(labels: list[str], width=30, max_lines=3) -> list[str]:
    if not labels:
        return []
    text = "; ".join(labels)
    lines = textwrap.wrap(text, width) or [""]
    if len(lines) > max_lines:
        shown = lines[:max_lines]
        shown[-1] = shown[-1][: width - 8].rstrip() + f"… (+{len(labels)})"
        return shown
    return lines


PH_SHORT = {"PH1": "tài khoản", "PH2": "danh mục", "PH3": "đào tạo", "PH4": "người học", "PH5": "khuôn mặt",
            "PH6": "điểm danh", "PH7": "thông báo", "PH8": "báo cáo", "PH9": "nhật ký"}


def short_name(node) -> str:
    kind, v = node
    if kind in ("P", "X"):
        name = proc_name(v)[1]
        return name[0].lower() + name[1:]
    return node_title(node)


def edge_text(e, d) -> list[str]:
    """Nhan tren so do: muc thap ghi ten that; muc cao gop thanh ten luong tong hop (chi tiet o tu dien luong)."""
    labels, lvl = e["labels"], d["level"]
    limit = {2: 99, 1: 2, 0: 2, -1: 2}[lvl]
    if len(labels) <= limit:
        return label_lines(labels, 30, 3)
    s, t = e["s"], e["d"]
    if lvl == -1:
        phs = []
        for o in e["origins"]:
            p = PH_SHORT.get(BY_FID[o]["ph"])
            if p and p not in phs:
                phs.append(p)
        head = ("yêu cầu, dữ liệu về: " if t == ("P", "0") else "kết quả về: ") + ", ".join(phs)
    elif s[0] == "E" and t[0] in "PX":
        head = "yêu cầu " + short_name(t)
    elif t[0] == "E" and s[0] in "PX":
        head = "kết quả " + short_name(s)
    else:
        head = "dữ liệu cho " + short_name(t)
    return wrap(f"{head} ({len(labels)} mục)", 32, 3)


def merge_entities(d) -> tuple[list[dict], dict]:
    """Gop cac tac nhan co CUNG ket noi (cung tien trinh, cung du lieu) thanh mot hop - chi khi ve."""
    sig: dict = {}
    for n in [n for n in d["nodes"] if n[0] == "E"]:
        key = tuple(sorted(("in" if e["d"] == n else "out", e["s"] if e["d"] == n else e["d"], tuple(e["labels"]))
                           for e in d["edges"] if n in (e["s"], e["d"])))
        sig.setdefault(key, []).append(n)
    order = [c for c, *_ in P.ENTITIES] + [c for c, _ in P.CONTEXT_ENTITIES]
    remap, names = {}, {}
    for members in sig.values():
        members.sort(key=lambda n: order.index(n[1]))
        merged = ("E", "+".join(m[1] for m in members))
        for m in members:
            remap[m] = merged
        names[merged] = ", ".join(entity_label(m[1], d["level"]) for m in members)
    edges: "OrderedDict[tuple, dict]" = OrderedDict()
    for e in d["edges"]:
        s, t = remap.get(e["s"], e["s"]), remap.get(e["d"], e["d"])
        x = edges.setdefault((s, t), {"s": s, "d": t, "labels": [], "kinds": set(), "origins": []})
        for lb in e["labels"]:
            if lb not in x["labels"]:
                x["labels"].append(lb)
        x["kinds"] |= e["kinds"]
        x["origins"] += [o for o in e["origins"] if o not in x["origins"]]
    return list(edges.values()), names


def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


class Labels:
    def __init__(self):
        self.boxes = []

    def free(self, box) -> bool:
        return all(box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3] for b in self.boxes)

    def place_text_on_curve(self, curve, lines, pref=0.5, lh=12.4):
        """Nhan chu: thu nhieu vi tri doc theo duong cong (t) va lech doc nho; tra (x, y) tam nhan."""
        w = max(len(s) for s in lines) * 6.0 + 10
        h = len(lines) * lh + 8
        ts = [pref] + [pref + d * k for k in (0.07, 0.14, 0.21, 0.28) for d in (1, -1)]
        for t in [t for t in ts if 0.12 <= t <= 0.88]:
            x, y = bez(*curve, t)
            for dy in (0, 9, -9, 18, -18):
                box = (x - w / 2, y + dy - h / 2, x + w / 2, y + dy + h / 2)
                if self.free(box):
                    self.boxes.append(box)
                    return x, y + dy
        x, y = bez(*curve, pref)
        return x, self.place(x, y, lines, lh)

    def place_on_curve(self, curve, r=10):
        """Tim diem trong doc theo duong cong (thu nhieu vi tri t) cho vong so ban kinh r."""
        for t in (0.5, 0.42, 0.58, 0.34, 0.66, 0.27, 0.73, 0.2, 0.8, 0.46, 0.54, 0.38, 0.62, 0.3, 0.7, 0.24, 0.76):
            x, y = bez(*curve, t)
            box = (x - r, y - r, x + r, y + r)
            if self.free(box):
                self.boxes.append(box)
                return x, y
        x, y = bez(*curve, 0.5)
        self.boxes.append((x - r, y - r, x + r, y + r))
        return x, y

    def place(self, x, y, lines, lh=12.4, anchor="middle"):
        w = max(len(s) for s in lines) * 6.0 + 10
        h = len(lines) * lh + 8
        x0 = x - w / 2 if anchor == "middle" else x - 4
        for k in range(0, 21):
            dy = (k + 1) // 2 * 13 * (1 if k % 2 else -1)
            box = (x0, y + dy - h / 2, x0 + w, y + dy + h / 2)
            if all(box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3] for b in self.boxes):
                self.boxes.append(box)
                return y + dy
        self.boxes.append((x0, y - h / 2, x0 + w, y + h / 2))
        return y


def text_block(x, y, lines, cls, lh=12.4, anchor="middle"):
    top = y - (len(lines) - 1) * lh / 2
    return "".join(f'<text class="{cls}" x="{x:.1f}" y="{top + i * lh + 4:.1f}" text-anchor="{anchor}">{esc(s)}</text>'
                   for i, s in enumerate(lines))


def edge_kind(e) -> str:
    k = e["kinds"]
    if k == {"read"}:
        return "read"
    if k == {"write"}:
        return "write"
    if "audit" in k and k <= {"audit"}:
        return "audit"
    if "event" in k and k <= {"event", "audit"}:
        return "event"
    return "data"


def node_title(n) -> str:
    kind, v = n
    if kind == "E":
        return ENT_NAME.get(v) or CTX_NAME.get(v, v)
    if kind == "S":
        return f"{v} — {STORE_NAME[v]}" + (f" ({', '.join(STORE_TABLES[v])})" if STORE_TABLES.get(v) else "")
    num, name = proc_name(v)
    return f"{num}. {name}"


def entity_label(code, level):
    return CTX_NAME[code] if level <= 0 and code in CTX_NAME and code not in ENT_NAME else ENT_NAME.get(code, CTX_NAME.get(code, code))


def legend_svg(x, y, show_audit=True) -> str:
    items = [("data", "luồng dữ liệu (có tên)"), ("read", "đọc kho"), ("write", "ghi kho"), ("rw", "đọc + ghi kho"),
             ("event", "sự kiện nội bộ (thông báo)")]
    if show_audit:
        items.append(("audit", "ghi vết nhật ký"))
    out = [f'<text class="lg" x="{x}" y="{y}" font-weight="700">Ký hiệu:</text>']
    cx = x + 58
    shapes = [f'<circle class="pc" cx="{cx + 10}" cy="{y - 4}" r="9"/><text class="lg" x="{cx + 24}" y="{y}">tiến trình</text>',
              f'<circle class="px" cx="{cx + 102}" cy="{y - 4}" r="9"/><text class="lg" x="{cx + 116}" y="{y}">tiến trình ngoài</text>',
              f'<rect class="en" x="{cx + 212}" y="{y - 12}" width="22" height="15" rx="2"/><text class="lg" x="{cx + 240}" y="{y}">tác nhân</text>',
              f'<line class="sl" x1="{cx + 300}" y1="{y - 12}" x2="{cx + 330}" y2="{y - 12}"/><line class="sl" x1="{cx + 300}" y1="{y + 3}" x2="{cx + 330}" y2="{y + 3}"/>'
              f'<text class="lg" x="{cx + 336}" y="{y}">kho dữ liệu</text>']
    out += shapes
    lx = cx + 420
    for k, t in items:
        out.append(f'<path class="e k-{k if k != "rw" else "rw"}" d="M{lx},{y - 4} L{lx + 30},{y - 4}" marker-end="url(#m-{k})"/>'
                   f'<text class="lg" x="{lx + 36}" y="{y}">{esc(t)}</text>')
        lx += 36 + len(t) * 5.8 + 18
    return "".join(out)


def svg_wrap(body: str, w: float, h: float, title: str, sub: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w:.0f}" '
            f'height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}"><style>{CSS_SVG}</style><defs>{MARKERS}</defs>'
            f'<rect width="100%" height="100%" fill="#ffffff"/>'
            f'<text class="ttl" x="24" y="30">{esc(title)}</text><text class="sub" x="24" y="48">{esc(sub)}</text>'
            f'{body}</svg>')


def render_context(d) -> tuple[str, float, float]:
    ents = sorted({n for n in d["nodes"] if n[0] == "E"}, key=lambda n: [c for c, _ in P.CONTEXT_ENTITIES].index(n[1]))
    W, H = 1280, 900
    cx, cy, R = W / 2, H / 2 + 10, 120
    pos = {}
    k = len(ents)
    for i, n in enumerate(ents):
        a = -math.pi / 2 + 2 * math.pi * i / k + math.pi / k
        pos[n] = (cx + 470 * math.cos(a), cy + 330 * math.sin(a))
    parts, labels = [], Labels()
    for e in d["edges"]:
        ent = e["s"] if e["s"][0] == "E" else e["d"]
        ex, ey = pos[ent]
        inbound = e["d"] == ("P", "0")
        ang = math.atan2(ey - cy, ex - cx)
        off = 0.11 if inbound else -0.11
        px, py = cx + R * math.cos(ang + off), cy + R * math.sin(ang + off)
        # diem tren bien hop tac nhan
        dx, dy = px - ex, py - ey
        sc = min((EW / 2 + 2) / abs(dx) if dx else 1e9, (EH / 2 + 2) / abs(dy) if dy else 1e9)
        nx, ny = -math.sin(ang), math.cos(ang)
        sh = 9 if inbound else -9
        bx, by = ex + dx * sc + nx * sh, ey + dy * sc + ny * sh
        p0, p3 = ((bx, by), (px, py)) if inbound else ((px, py), (bx, by))
        mx, my = (p0[0] + p3[0]) / 2, (p0[1] + p3[1]) / 2
        p1 = (p0[0] * .6 + mx * .4 + nx * sh * 2, p0[1] * .6 + my * .4 + ny * sh * 2)
        p2 = (p3[0] * .6 + mx * .4 + nx * sh * 2, p3[1] * .6 + my * .4 + ny * sh * 2)
        title = esc(f"{node_title(e['s'])} → {node_title(e['d'])}: " + "; ".join(e["labels"]))
        parts.append(f'<path class="e k-data" d="M{p0[0]:.1f},{p0[1]:.1f} C{p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} '
                     f'{p3[0]:.1f},{p3[1]:.1f}" marker-end="url(#m-data)"><title>{title}</title></path>')
        lines = edge_text(e, d)
        if lines:
            lx, ly = bez(p0, p1, p2, p3, 0.5)
            ly = labels.place(lx + nx * sh * 2.4, ly + ny * sh * 2.4, lines)
            parts.append(text_block(lx + nx * sh * 2.4, ly, lines, "lb"))
    parts.append(f'<a href="#L0"><title>Mở DFD mức 0</title><circle class="pc" cx="{cx}" cy="{cy}" r="{R}"/>'
                 + text_block(cx, cy - 34, ["0"], "pid") + text_block(cx, cy + 8, wrap(proc_name("0")[1], 22, 4), "pn", 14) + "</a>")
    for n in ents:
        x, y = pos[n]
        parts.append(f'<g><title>{esc(node_title(n))}</title><rect class="en" x="{x - EW / 2:.1f}" y="{y - EH / 2:.1f}" '
                     f'width="{EW}" height="{EH}" rx="4"/>' + text_block(x, y, wrap(entity_label(n[1], -1), 26, 3), "et") + "</g>")
    parts.append(legend_svg(24, H - 20, show_audit=False))
    return "".join(parts), W, H


def render_columns(d) -> tuple[str, float, float]:
    edges, ent_names = merge_entities(d)
    internal = [n for n in d["internal"]]
    externals = sorted({n for n in d["nodes"] if n[0] == "X"}, key=lambda n: nkey(n[1]) if n[1][0].isdigit() else (99,))
    procs = internal + externals
    ents = sorted({x for e in edges for x in (e["s"], e["d"]) if x[0] == "E"})
    stores = [n for n in d["nodes"] if n[0] == "S"]
    p2p = [e for e in edges if e["s"][0] in "PX" and e["d"][0] in "PX"]
    n_p = len(procs)
    step_p = 150 if n_p > 1 else 170
    top = 92
    x_e = 30 + EW / 2
    x_p = x_e + EW / 2 + 430 + R_PROC
    arc_room = 0 if not p2p else min(240, 70 + 26 * len(p2p))
    x_s = x_p + R_PROC + 260 + arc_room + SW / 2
    pos = {}
    for i, n in enumerate(procs):
        pos[n] = (x_p, top + R_PROC + i * step_p)
    h_p = top + n_p * step_p

    def bary(n):
        ys = [pos[e["d"] if e["s"] == n else e["s"]][1] for e in edges if (e["s"] == n or e["d"] == n)
              and (e["d"] if e["s"] == n else e["s"]) in pos]
        return sum(ys) / len(ys) if ys else 0

    ent_order = [c for c, *_ in P.ENTITIES] + [c for c, _ in P.CONTEXT_ENTITIES]
    ents.sort(key=lambda n: (bary(n), ent_order.index(n[1].split('+')[0])))
    store_order = [c for c, *_ in STORES] + [c for c, *_ in P.EXTRA_STORES]
    stores.sort(key=lambda n: (bary(n), store_order.index(n[1])))

    def spread(nodes, x, min_step):
        if not nodes:
            return
        ys = [bary(n) for n in nodes]
        # bat dau tu barycenter, roi day ra cho du khoang cach toi thieu
        placed = []
        for y in ys:
            y = max(y, (placed[-1] + min_step) if placed else top + 30)
            placed.append(y)
        # can giua lai neu tran xuong duoi
        overflow = placed[-1] - max(h_p - 40, placed[-1])
        for i, n in enumerate(nodes):
            pos[n] = (x, placed[i] - max(0, overflow))
    spread(ents, x_e, EH + 26)
    spread(stores, x_s, SH + 22)
    H = max(y for _x, y in pos.values()) + 120
    W = x_s + SW / 2 + 40
    parts, labels = [], Labels()

    # --- canh
    pair_dirs = {}
    for e in edges:
        pair_dirs.setdefault(frozenset((e["s"], e["d"])), []).append(e)
    store_pairs = {}
    for e in edges:
        if e["s"][0] == "S" or e["d"][0] == "S":
            proc = e["d"] if e["s"][0] == "S" else e["s"]
            st = e["s"] if e["s"][0] == "S" else e["d"]
            store_pairs.setdefault((proc, st), set()).add("R" if e["s"][0] == "S" else "W")
    arc_i = 0
    numbered, num_rows = d["level"] == 0, []
    for e in edges:
        s, t = e["s"], e["d"]
        kind = edge_kind(e)
        both = len(pair_dirs[frozenset((s, t))]) > 1
        tip = esc(f"{node_title(s)} → {node_title(t)}" + (": " + "; ".join(e["labels"]) if e["labels"] else "")
                  + "\nPhân rã từ: " + ", ".join(BY_FID[o]["id"] for o in e["origins"]))
        if s[0] == "S" or t[0] == "S":
            proc = t if s[0] == "S" else s
            st = s if s[0] == "S" else t
            modes = store_pairs[(proc, st)]
            if s[0] == "S" and "W" in modes:
                continue  # ve 1 lan cho canh doc+ghi
            k = "rw" if modes == {"R", "W"} else ("read" if modes == {"R"} else "write")
            px, py = pos[proc]
            sx, sy = pos[st]
            ang = math.atan2(sy - py, sx - px)
            p0 = (px + R_PROC * math.cos(ang), py + R_PROC * math.sin(ang))
            p3 = (sx - SW / 2, sy)
            dx = p3[0] - p0[0]
            p1, p2 = (p0[0] + dx * .45, p0[1]), (p3[0] - dx * .45, p3[1])
            ms = ' marker-start="url(#m-rw)"' if k == "rw" else (' marker-start="url(#m-read)"' if k == "read" else "")
            me = ' marker-end="url(#m-rw)"' if k == "rw" else (' marker-end="url(#m-write)"' if k == "write" else "")
            parts.append(f'<path class="e k-{k}" d="M{p0[0]:.1f},{p0[1]:.1f} C{p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} '
                         f'{p3[0]:.1f},{p3[1]:.1f}"{ms}{me}><title>{tip}</title></path>')
            continue
        if s[0] == "E" or t[0] == "E":
            ent = s if s[0] == "E" else t
            proc = t if s[0] == "E" else s
            inbound = s[0] == "E"
            ex, ey = pos[ent]
            px, py = pos[proc]
            off = (9 if inbound else -9) if both else 0
            aoff = (0.13 if inbound else -0.13) if both else 0
            ang = math.atan2(ey - py, ex - px) + (-aoff if inbound else aoff)
            pp = (px + R_PROC * math.cos(ang), py + R_PROC * math.sin(ang))
            ee = (ex + EW / 2, ey + off)
            p0, p3 = (ee, pp) if inbound else (pp, ee)
            dx = p3[0] - p0[0]
            p1, p2 = (p0[0] + dx * .45, p0[1]), (p3[0] - dx * .45, p3[1])
            parts.append(f'<path class="e k-{kind}" d="M{p0[0]:.1f},{p0[1]:.1f} C{p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},'
                         f'{p2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}" marker-end="url(#m-{kind})"><title>{tip}</title></path>')
            lines = edge_text(e, d)
            if lines and numbered:
                # Muc 0: tren mui ten chi ghi so; noi dung o bang tu dien luong ben duoi hinh.
                num = len(num_rows) + 1
                num_rows.append((num, e, lines))
                lx, ly = labels.place_on_curve((p0, p1, p2, p3))
                parts.append(f'<g><title>{tip}</title><circle cx="{lx:.1f}" cy="{ly:.1f}" r="9" fill="#fff" stroke="#334155"/>'
                             f'<text class="lb" x="{lx:.1f}" y="{ly + 3.6:.1f}" text-anchor="middle" font-weight="700">{num}</text></g>')
            elif lines:
                lx, ly = labels.place_text_on_curve((p0, p1, p2, p3), lines, 0.38 if inbound else 0.62)
                parts.append(text_block(lx, ly, lines, f"lb lb-{kind}"))
            continue
        # tien trinh <-> tien trinh: cung tron ben phai cot tien trinh
        (sx, sy), (tx, ty) = pos[s], pos[t]
        down = ty > sy
        a0, a1 = (0.45, -0.45) if down else (-0.45, 0.45)
        p0 = (sx + R_PROC * math.cos(a0), sy + R_PROC * math.sin(a0))
        p3 = (tx + R_PROC * math.cos(a1), ty + R_PROC * math.sin(a1))
        bulge = max(p0[0], p3[0]) + 34 + min(200, 0.16 * abs(ty - sy)) + (18 if both and not down else 0) + (arc_i % 3) * 6
        arc_i += 1
        p1, p2 = (bulge, p0[1]), (bulge, p3[1])
        cls = f"e k-{kind}" + (" audit" if kind == "audit" else "")
        parts.append(f'<path class="{cls}" d="M{p0[0]:.1f},{p0[1]:.1f} C{p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} '
                     f'{p3[0]:.1f},{p3[1]:.1f}" marker-end="url(#m-{kind})"><title>{tip}</title></path>')
        lines = edge_text(e, d)[:2]
        if lines:
            lx, ly = bez(p0, p1, p2, p3, 0.5)
            ly = labels.place(lx + 4, ly, lines, anchor="start")
            parts.append(text_block(lx + 4, ly, lines, f"lb lb-{kind}" + (" audit" if kind == "audit" else ""), anchor="start"))

    # --- nut
    for n in procs:
        x, y = pos[n]
        num, name = proc_name(n[1])
        href = diagram_href(n[1])
        cls, idc = ("pc", "pid") if n[0] == "P" else ("px", "pxid")
        body = (f'<title>{esc(num + ". " + name)}</title><circle class="{cls}" cx="{x}" cy="{y}" r="{R_PROC}"/>'
                + text_block(x, y - R_PROC + 19, [num], idc)
                + f'<line x1="{x - R_PROC + 9}" y1="{y - R_PROC + 27}" x2="{x + R_PROC - 9}" y2="{y - R_PROC + 27}" '
                  f'stroke="{"#ea580c" if n[0] == "P" else "#94a3b8"}" stroke-width="1"/>'
                + text_block(x, y + 9, wrap(name, 17, 4), "pn", 12.2))
        parts.append(f'<a href="{href}">{body}</a>' if href else f"<g>{body}</g>")
    for n in ents:
        x, y = pos[n]
        link = f"dac_ta_chuc_nang.html?tac_nhan={n[1]}" if n[1] in ENT_NAME else ""
        nm = ent_names.get(n, entity_label(n[1], d["level"]))
        lines_e = wrap(nm, 26, 4)
        eh = max(EH, 14 + 13 * len(lines_e))
        body = (f'<title>{esc(nm)}</title><rect class="en" x="{x - EW / 2:.1f}" y="{y - eh / 2:.1f}" '
                f'width="{EW}" height="{eh}" rx="4"/>' + text_block(x, y, lines_e, "et", 13))
        parts.append(f'<a href="{link}">{body}</a>' if link else f"<g>{body}</g>")
    for n in stores:
        x, y = pos[n]
        tabs = STORE_TABLES.get(n[1]) or []
        href = f"csdl_chi_tiet.html#{tabs[0]}" if tabs else ""
        x0 = x - SW / 2
        body = (f'<title>{esc(node_title(n))}</title><rect x="{x0}" y="{y - SH / 2}" width="{SW}" height="{SH}" fill="#f0fdfa"/>'
                f'<line class="sl" x1="{x0}" y1="{y - SH / 2}" x2="{x0 + SW}" y2="{y - SH / 2}"/>'
                f'<line class="sl" x1="{x0}" y1="{y + SH / 2}" x2="{x0 + SW}" y2="{y + SH / 2}"/>'
                f'<rect class="sc" x="{x0}" y="{y - SH / 2}" width="36" height="{SH}"/>'
                + text_block(x0 + 18, y, [n[1]], "sid")
                + text_block(x0 + 44, y, wrap(STORE_NAME[n[1]].split(" (")[0], 30, 2), "st", 12, anchor="start"))
        parts.append(f'<a href="{href}">{body}</a>' if href else f"<g>{body}</g>")
    if num_rows:
        # bang tu dien luong (2 cot) ngay duoi so do muc 0 - de anh xuat ra van doc duoc
        y0 = H - 70
        parts.append(f'<text class="lg" x="24" y="{y0}" font-weight="700">Từ điển luồng (số trên mũi tên → nội dung; '
                     f'chi tiết từng mục ở bảng trên trang dfd.html):</text>')
        colw = (W - 60) / 2
        per_col = (len(num_rows) + 1) // 2
        yy = [y0 + 18, y0 + 18]
        for i, (num, e, lines) in enumerate(num_rows):
            c = 0 if i < per_col else 1
            ent = e["s"] if e["s"][0] == "E" else e["d"]
            proc = e["d"] if e["s"][0] == "E" else e["s"]
            who = ent_names.get(ent, entity_label(ent[1], d["level"]))
            arrow = f"{who} → {proc_name(proc[1])[0]}" if e["s"][0] == "E" else f"{proc_name(proc[1])[0]} → {who}"
            txt = f"{num}. {arrow}: " + " ".join(lines)
            for j, ln in enumerate(textwrap.wrap(txt, int(colw / 5.7)) or [""]):
                parts.append(f'<text class="lg" x="{24 + c * colw + (0 if j == 0 else 16):.1f}" y="{yy[c]:.1f}">{esc(ln)}</text>')
                yy[c] += 13.5
            yy[c] += 2
        H = max(yy) + 50
    parts.append(legend_svg(24, H - 24))
    return "".join(parts), W, H


def render(d) -> tuple[str, float, float]:
    body, w, h = render_context(d) if d["id"] == "CTX" else render_columns(d)
    sub = {"CTX": "Toàn bộ hệ thống là một tiến trình; chỉ thể hiện trao đổi với tác nhân ngoài.",
           "L0": "Mỗi tiến trình là một phân hệ; kho dữ liệu D1–D9 (CSDL), M1 (bộ nhớ), F1 (thư mục ảnh)."}.get(
        d["id"], "Luồng tới kho không đặt tên (cả bản ghi). Bấm tiến trình để xem mức sâu hơn / đặc tả.")
    return svg_wrap(body, w, h, d["title"] + " — " + PROJECT["short"], sub), w, h


# ============================================================================ so do phan ra (BFD)
def render_bfd() -> tuple[str, float, float]:
    colw, gap = 214, 12
    n = len(PHS)
    W = 30 + n * (colw + gap) + 20
    root_y, ph_y, ph_h = 70, 140, 58
    parts = []
    cxr = W / 2
    parts.append(f'<rect x="{cxr - 170}" y="{root_y - 26}" width="340" height="52" rx="8" fill="#0f2a3d"/>'
                 + text_block(cxr, root_y, [PROJECT["short"] + " — " + "Hệ thống điểm danh bằng khuôn mặt"], "bt-root"))
    bar_y = root_y + 26 + 22
    parts.append(f'<line x1="{cxr}" y1="{root_y + 26}" x2="{cxr}" y2="{bar_y}" class="bl"/>')
    xs = [30 + i * (colw + gap) for i in range(n)]
    parts.append(f'<line x1="{xs[0] + colw / 2}" y1="{bar_y}" x2="{xs[-1] + colw / 2}" y2="{bar_y}" class="bl"/>')
    max_y = 0
    for i, ph in enumerate(PHS):
        x0 = xs[i]
        col = ph["color"]
        parts.append(f'<line x1="{x0 + colw / 2}" y1="{bar_y}" x2="{x0 + colw / 2}" y2="{ph_y}" class="bl"/>')
        href = f"dfd.html#L1-{ph['code']}" if ph["dfd"] else f"dac_ta_chuc_nang.html#{GROUPS[ph['groups'][0]]['leaves'][0]}"
        parts.append(f'<a href="{href}"><title>{esc(ph["code"] + ". " + ph["name"])}</title><rect x="{x0}" y="{ph_y}" width="{colw}" '
                     f'height="{ph_h}" rx="7" fill="{col}"/>'
                     + text_block(x0 + colw / 2, ph_y + 17, [f"{ph['n']}. {ph['code']}"], "bt-ph-id")
                     + text_block(x0 + colw / 2, ph_y + 38, wrap(ph["name"], 30, 2), "bt-ph") + "</a>")
        y = ph_y + ph_h + 16
        spine_top = ph_y + ph_h
        last_mid = spine_top
        for gid in ph["groups"]:
            g = GROUPS[gid]
            glines = wrap(f"{gid} {g['name']}", 30, 2)
            gh = 12 + 13 * len(glines)
            gx = x0 + 14
            parts.append(f'<line x1="{x0 + 6}" y1="{y + gh / 2}" x2="{gx}" y2="{y + gh / 2}" class="bl"/>')
            ghref = diagram_href(gid)
            ghref = ("dfd.html" + ghref) if ghref.startswith("#") else ghref
            parts.append(f'<a href="{ghref}"><title>{esc(gid + " " + g["name"])}</title><rect x="{gx}" y="{y}" width="{colw - 14}" '
                         f'height="{gh}" rx="5" fill="#ffffff" stroke="{col}" stroke-width="1.8"/>'
                         + text_block(gx + (colw - 14) / 2, y + gh / 2, glines, "bt-g", 13) + "</a>")
            last_mid = y + gh / 2
            ly = y + gh + 8
            lsp_top = y + gh
            l_last = lsp_top
            for lid in g["leaves"]:
                lf = BY_ID[lid]
                lines = wrap(f"{lid} {lf['name']}", 31, 3)
                lh = 8 + 11.6 * len(lines)
                lx = x0 + 30
                parts.append(f'<line x1="{x0 + 22}" y1="{ly + lh / 2}" x2="{lx}" y2="{ly + lh / 2}" class="bl2"/>')
                parts.append(f'<a href="dac_ta_chuc_nang.html#{lid}"><title>{esc(lid + " " + lf["name"] + " (mã tính năng " + lf["fid"] + ")")}</title>'
                             f'<rect x="{lx}" y="{ly}" width="{colw - 30}" height="{lh}" rx="4" fill="{tint(col)}" stroke="{col}" '
                             f'stroke-width=".8"/>' + text_block(lx + 6, ly + lh / 2, lines, "bt-l", 11.6, anchor="start") + "</a>")
                l_last = ly + lh / 2
                ly += lh + 5
            parts.append(f'<line x1="{x0 + 22}" y1="{lsp_top}" x2="{x0 + 22}" y2="{l_last}" class="bl2"/>')
            y = ly + 8
        parts.append(f'<line x1="{x0 + 6}" y1="{spine_top}" x2="{x0 + 6}" y2="{last_mid}" class="bl"/>')
        max_y = max(max_y, y)
    H = max_y + 30
    css = (CSS_SVG + ".bl{stroke:#475569;stroke-width:1.4}.bl2{stroke:#94a3b8;stroke-width:1}"
           ".bt-root{font-size:14px;font-weight:800;fill:#fff}.bt-ph-id{font-size:12px;font-weight:800;fill:#fff}"
           ".bt-ph{font-size:11.5px;font-weight:700;fill:#fff}.bt-g{font-size:11.2px;font-weight:700;fill:#0f172a}"
           ".bt-l{font-size:10.4px;fill:#1f2937}")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">'
           f'<style>{css}</style><rect width="100%" height="100%" fill="#fff"/>'
           f'<text class="ttl" x="24" y="28">Sơ đồ phân rã chức năng (BFD) — {esc(PROJECT["short"])}</text>'
           f'{"".join(parts)}</svg>')
    return svg, W, H


def tint(hex_color: str, k=0.9) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(round(v + (255 - v) * k) for v in (r, g, b))


# ============================================================================ du lieu trang dac ta
JUNIT = FI._load_junit(ROOT / "server" / "junit.xml")
FLUTTER = FI._load_flutter(ROOT / "client" / "flutter_results.json")
E2E = json.loads((TOOLS / "e2e_results.json").read_text(encoding="utf-8")) if (TOOLS / "e2e_results.json").exists() else {}
TEST_LINE = {}
for py in (ROOT / "server" / "tests").glob("test_*.py"):
    for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"(?:async\s+)?def (test_\w+)\(", line)
        if m:
            TEST_LINE[f"{py.name}::{m.group(1)}"] = i


def gh_link(file: str, line: int | None = None) -> str:
    return GH + file + (f"#L{line}" if line else "")


def test_items(leaf) -> list[dict]:
    seen, items = set(), []

    def add(name, origin):
        if name in seen:
            return
        seen.add(name)
        if name.startswith("flutter:"):
            f = name[8:]
            items.append({"name": f, "status": FLUTTER.get(f, "?"), "href": gh_link(f"client/test/{f}"), "origin": origin})
        elif name.startswith("e2e:"):
            items.append({"name": f"E2E trình duyệt: {name[4:]}", "status": E2E.get(name[4:], "?"),
                          "href": gh_link("docs/TEST_REPORT.md"), "origin": origin})
        elif "::" in name:
            line = TEST_LINE.get(name)
            items.append({"name": name, "status": JUNIT.get(name, "?"), "href": gh_link(f"server/tests/{name.split('::')[0]}", line),
                          "origin": origin})
        else:
            sts = [v for k, v in JUNIT.items() if k.startswith(name + "::")]
            items.append({"name": name + f" (cả tệp, {len(sts)} test)", "status": "failed" if "failed" in sts else ("passed" if sts else "?"),
                          "href": gh_link(f"server/tests/{name}"), "origin": origin})
    for ev in FEATS[leaf["fid"]]["evidence"]:
        add(ev, "danh mục")
    traced = []
    for key in leaf["routes"] + leaf["jobs"]:
        traced += [t.replace("tests/", "") for t in SQL.get(key, {}).get("tests", [])]
    words = set(re.findall(r"[a-z]{4,}", " ".join(leaf["routes"] + leaf["jobs"]).lower()))
    traced = sorted(set(traced), key=lambda t: (-sum(w in t for w in words), t))
    total = len(traced)
    for t in traced[:10]:
        add(t, "gọi khi chạy")
    return items, total


def chain_json(node) -> dict:
    return {"fn": node["fn"].replace("app.", ""), "layer": node["layer"], "href": gh_link(node["file"], node["line"]),
            "rec": node.get("recursive", False), "c": [chain_json(c) for c in node["children"]]}


def route_info(rk: str) -> dict:
    r = CODE["routes"][rk]
    usages = CODE["client"]["usages"].get(rk, [])
    methods = [{"call": k, "href": gh_link(v["file"], v["line"])} for k, v in CODE["client"]["methods"].items() if v["route"] == rk]
    return {
        "key": rk, "auth": r["auth"], "roles": [ROLE_VN.get(x, x) for x in r["roles"]], "summary": r["summary"],
        "doc": r["doc"], "params": r["params"], "body": r["body"], "response": r["response"],
        "controller": {"fn": r["endpoint"]["fn"].replace("app.", ""), "href": gh_link(r["endpoint"]["file"], r["endpoint"]["line"])},
        "chain": chain_json(r["chain"]),
        "errors": [{"status": e["status"], "msg": e["msg"], "at": e["at"].replace("app.", ""),
                    "href": gh_link(e["file"], e["line"])} for e in r["errors"]],
        "sql": {k: SQL.get(rk, {}).get("ok", {}).get(k, []) for k in ("R", "W")},
        "sql_other": {side: SQL.get(rk, {}).get(side) for side in ("ok_auth", "ok_notify", "ok_audit")
                      if SQL.get(rk, {}).get(side)},
        "client": [{"call": u["call"], "href": gh_link(u["file"], u["line"]), "file": u["file"],
                    "screens": u["screens"]} for u in usages],
        "api_methods": methods,
    }


def job_info(jk: str) -> dict:
    j = CODE["jobs"][jk]
    return {"key": jk, "loop": j["loop"].replace("app.", ""), "loop_href": gh_link(j["loop_file"], j["loop_line"]),
            "doc": j["doc"], "chain": chain_json(j["chain"]),
            "errors": [{"status": e["status"], "msg": e["msg"], "at": e["at"].replace("app.", ""),
                        "href": gh_link(e["file"], e["line"])} for e in j["errors"]],
            "sql": {k: SQL.get(jk, {}).get("ok", {}).get(k, []) for k in ("R", "W")}}


def node_ref(n) -> dict:
    kind, v = n
    if kind == "E":
        return {"t": "E", "id": v, "name": ENT_NAME[v]}
    if kind == "S":
        tabs = STORE_TABLES.get(v) or []
        return {"t": "S", "id": v, "name": STORE_NAME[v], "href": f"csdl_chi_tiet.html#{tabs[0]}" if tabs else ""}
    lf = BY_FID[v]
    return {"t": "P", "id": lf["id"], "name": lf["name"], "href": f"#{lf['id']}"}


def where_used(leaf) -> list[dict]:
    out = []
    ph = PH_BY_CODE[leaf["ph"]]
    if ph["dfd"]:
        out.append({"t": f"DFD mức 1 — tiến trình {ph['n']}. {ph['name']}", "href": f"dfd.html#L1-{leaf['ph']}"})
        if f"L2-{leaf['group']}" in DIAGRAMS:
            out.append({"t": f"DFD mức 2 — tiến trình {leaf['group']}. {GROUPS[leaf['group']]['name']}",
                        "href": f"dfd.html#L2-{leaf['group']}"})
    out.append({"t": "Sơ đồ phân rã chức năng", "href": f"phan_ra_chuc_nang.html#{leaf['id']}"})
    wf = next((f for f in FLOWS if f["key"] == leaf["ph"].lower()), None)
    if wf:
        out.append({"t": f"Sơ đồ quy trình — {wf['tab']}", "href": f"workflow_tong_quan.html#func:{wf['key']}"})
    for r in leaf["roles"]:
        out.append({"t": f"Cây chức năng — {ROLE_VN[r]}", "href": f"chuc_nang_cay.html#{ROLE_ID[r]}"})
    return out


def leaf_json(leaf) -> dict:
    tests, total = test_items(leaf)
    flows = [{"s": node_ref(f["s"]), "d": node_ref(f["d"]), "label": f["label"], "kind": f["kind"]}
             for f in FLOWS_LEAF if f["origin"] == leaf["fid"] or (f["kind"] in ("data", "event", "audit") and
                                                                   (f["d"] == ("P", leaf["fid"]) and f["origin"] != leaf["fid"]))]
    fns = []
    for f in leaf["fns"]:
        info = CODE["functions"][f]
        fns.append({"fn": f.replace("app.", ""), "href": gh_link(info["file"], info["line"]), "doc": info["doc"],
                    "errors": [{"status": e["status"], "msg": e["msg"]} for e in info["errors"]]})
    feat = FEATS[leaf["fid"]]
    return {
        "id": leaf["id"], "fid": leaf["fid"], "name": leaf["name"], "ph": leaf["ph"], "phn": PH_BY_CODE[leaf["ph"]]["n"],
        "phname": PH_BY_CODE[leaf["ph"]]["name"], "group": leaf["group"], "gname": GROUPS[leaf["group"]]["name"],
        "ghref": (f"dfd.html#L2-{leaf['group']}" if f"L2-{leaf['group']}" in DIAGRAMS else
                  f"dfd.html#L1-{leaf['ph']}" if PH_BY_CODE[leaf["ph"]]["dfd"] else f"phan_ra_chuc_nang.html#{leaf['id']}"),
        "color": PH_BY_CODE[leaf["ph"]]["color"], "kind": leaf["kind"], "actor": feat["actor"], "screen": feat["screen"],
        "change": feat["change"], "ents": [{"id": e, "name": ENT_NAME[e]} for e in leaf["ents"]],
        "roles": [ROLE_VN[r] for r in leaf["roles"]], "role_ids": leaf["roles"],
        "vao": leaf.get("vao", ""), "ra": leaf.get("ra", ""), "xl": leaf.get("xl", []), "note": leaf.get("note", ""),
        "R": leaf["R"], "W": leaf["W"], "RW": leaf["RW"],
        "stores": {k: sorted(v) for k, v in leaf["stores"].items()},
        "redirects": [{"to": BY_FID[o]["id"], "label": lb, "table": tb} for o, lb, _k, tb in leaf["redirects"]],
        "flows": flows, "routes": [route_info(r) for r in leaf["routes"]], "jobs": [job_info(j) for j in leaf["jobs"]],
        "fns": fns, "files": [{"f": f, "href": gh_link(f)} for f in leaf["files"]],
        "tests": tests, "tests_total": total, "used": where_used(leaf),
    }


# ============================================================================ kiem tra
def checks() -> list[str]:
    msgs = []
    routes_used = {r for lf in LEAVES for r in lf["routes"]}
    missing = sorted(set(CODE["routes"]) - routes_used)
    msgs.append(f"route thuoc it nhat 1 chuc nang la: {len(routes_used)}/{len(CODE['routes'])}" + (f" THIEU {missing}" if missing else ""))
    jobs_used = {j for lf in LEAVES for j in lf["jobs"]}
    msgs.append(f"tac vu nen: {len(jobs_used)}/{len(CODE['jobs'])}")
    tabs = {t for lf in LEAVES for t in lf["R"] + lf["W"] + lf["RW"]}
    msgs.append(f"bang duoc it nhat 1 chuc nang doc/ghi: {len(tabs & set(TABLES))}/{len(TABLES)}"
                + (f" THIEU {sorted(set(TABLES) - tabs)}" if set(TABLES) - tabs else ""))
    no_flow = [lf["id"] for lf in LEAVES if lf["ph"] not in P.NO_DFD
               and not any(f["origin"] == lf["fid"] or f["d"] == ("P", lf["fid"]) or f["s"] == ("P", lf["fid"]) for f in FLOWS_LEAF)]
    msgs.append(f"chuc nang la co luong du lieu: {sum(1 for lf in LEAVES if lf['ph'] not in P.NO_DFD) - len(no_flow)}/"
                f"{sum(1 for lf in LEAVES if lf['ph'] not in P.NO_DFD)}" + (f" KHONG CO: {no_flow}" if no_flow else ""))
    ok = sum(1 for v in BALANCE.values() if v[0])
    msgs.append(f"can bang giua cac muc: {ok}/{len(BALANCE)} so do" +
                "".join(f"\n   LECH {k}: {v[2]}" for k, v in BALANCE.items() if not v[0]))
    return msgs


# ============================================================================ trang HTML
NAV = [("workflow_tong_quan.html", "Sơ đồ quy trình"), ("erd_csdl.html", "CSDL (ERD)"),
       ("csdl_chi_tiet.html", "Chi tiết từng bảng CSDL"), ("chuc_nang_cay.html", "Sơ đồ chức năng cây"),
       ("phan_ra_chuc_nang.html", "Phân rã chức năng"), ("dfd.html", "DFD các mức"),
       ("dac_ta_chuc_nang.html", "Đặc tả & truy vết"), ("chuan_hoa_csdl.html", "Chuẩn hóa CSDL (4NF)")]


def nav_html(active: str) -> str:
    return '<nav class="top">' + "".join(f'<a href="{h}" class="{"on" if h == active else ""}">{t}</a>' for h, t in NAV) + "</nav>"


BASE_CSS = """*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI",system-ui,-apple-system,sans-serif;background:#f4f6f8;color:#1f2937}
nav.top{display:flex;gap:6px;flex-wrap:wrap;padding:10px 24px;background:#0f2a3d;position:sticky;top:0;z-index:5}
nav.top a{color:#cbd5e1;text-decoration:none;font-size:13px;font-weight:600;padding:7px 14px;border-radius:8px}
nav.top a:hover{background:rgba(255,255,255,.1)}nav.top a.on{background:#0e9594;color:#fff}
h1{margin:0;font-size:21px}.sbt{color:#64748b;font-size:13px;margin-top:4px}a{color:#0369a1}
.lay{display:flex;flex-wrap:wrap}aside{flex:0 0 300px;background:#fff;border-right:1px solid #e2e8f0;padding:12px;
height:calc(100vh - 52px);overflow:auto;position:sticky;top:52px}main{flex:1;min-width:0;padding:20px 26px}
aside .g{font-size:11px;font-weight:800;letter-spacing:.04em;margin:14px 6px 6px;text-transform:uppercase}
aside a.it{display:block;padding:5px 9px;border-radius:7px;font-size:12.6px;color:#334155;text-decoration:none}
aside a.it:hover{background:#f1f5f9}aside a.it.on{background:#e0f2f1;font-weight:700;color:#0f766e}
aside .sg{font-size:12px;font-weight:700;color:#475569;margin:8px 6px 2px}
table{border-collapse:collapse;width:100%;background:#fff;font-size:12.8px;margin:8px 0 16px}
th,td{border:1px solid #e2e8f0;padding:6px 9px;text-align:left;vertical-align:top}th{background:#f1f5f9}
code{background:#f1f5f9;padding:1px 6px;border-radius:5px;font-size:12px}.pill{display:inline-block;padding:1px 8px;
border-radius:999px;font-size:11.5px;font-weight:700;margin:1px 3px 1px 0}.pr{background:#dbeafe;color:#1e40af}
.pw{background:#ffedd5;color:#9a3412}.prw{background:#ede9fe;color:#5b21b6}.ok{background:#dcfce7;color:#166534}
.bad{background:#fee2e2;color:#991b1b}.unk{background:#f1f5f9;color:#475569}h3{margin:18px 0 6px;font-size:15.5px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin-bottom:14px}
.muted{color:#64748b}.tag{padding:3px 10px;border-radius:999px;color:#fff;font-size:12px;font-weight:700}
"""


def write_bfd_page(svg: str, w: float) -> None:
    rows = []
    for ph in PHS:
        n_leaf = sum(len(GROUPS[g]["leaves"]) for g in ph["groups"])
        rows.append(f'<tr><td><b style="color:{ph["color"]}">{ph["n"]}. {ph["code"]}</b></td><td>{esc(ph["name"])}</td>'
                    f'<td>{len(ph["groups"])}</td><td>{n_leaf}</td><td>'
                    + ("".join(f'<a href="dfd.html#L1-{ph["code"]}">DFD mức 1</a>' for _ in [0]) if ph["dfd"] else '<span class="muted">không vẽ DFD (hỗ trợ giao diện)</span>')
                    + "</td></tr>")
    tree = []
    for ph in PHS:
        tree.append(f'<li><b style="color:{ph["color"]}">{ph["n"]}. {esc(ph["name"])}</b><ul>')
        for gid in ph["groups"]:
            g = GROUPS[gid]
            tree.append(f'<li><b>{gid} {esc(g["name"])}</b><ul>')
            for lid in g["leaves"]:
                lf = BY_ID[lid]
                tree.append(f'<li id="{lid}"><a href="dac_ta_chuc_nang.html#{lid}">{lid} {esc(lf["name"])}</a> '
                            f'<span class="muted">· mã tính năng {lf["fid"]}</span></li>')
            tree.append("</ul></li>")
        tree.append("</ul></li>")
    page = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Phân rã chức năng - {PROJECT['short']}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>{BASE_CSS}
.wrap{{padding:20px 26px}}.canvas{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:auto;margin-top:12px}}
.tree ul{{list-style:none;padding-left:20px;border-left:1px dashed #cbd5e1;margin:4px 0}}.tree li{{margin:3px 0;font-size:13px}}
.tree li:target{{background:#fef9c3}}.zoom button{{border:1px solid #cbd5e1;background:#fff;border-radius:7px;padding:4px 10px;cursor:pointer}}
</style></head><body>{nav_html("phan_ra_chuc_nang.html")}<div class="wrap">
<h1>Sơ đồ phân rã chức năng (BFD) — {esc(PROJECT['short'])}</h1>
<div class="sbt">Hệ thống → {len(PHS)} phân hệ → {len(GROUPS)} chức năng cấp 2 → {len(LEAVES)} chức năng lá (tận cùng).
Số hiệu theo chuẩn PTTK (vd 6.3.5); "mã tính năng" là mã trong <a href="https://github.com/jfgafgfagfbja/FAMS-SYSTEM/blob/main/docs/FEATURE_INVENTORY.md">FEATURE_INVENTORY.md</a> (gắn với test).
Bấm phân hệ → DFD mức 1; chức năng cấp 2 → DFD mức 2; chức năng lá → đặc tả + truy vết code.</div>
<table style="max-width:900px"><tr><th>Phân hệ</th><th>Tên</th><th>Chức năng cấp 2</th><th>Chức năng lá</th><th>Phân rã luồng</th></tr>{"".join(rows)}</table>
<div class="zoom">Phóng to / thu nhỏ: <button onclick="z(-.1)">−</button> <button onclick="z(0)">100%</button> <button onclick="z(.1)">+</button>
 · <a href="phan_ra_chuc_nang.svg" download>Tải SVG</a> · <a href="phan_ra_chuc_nang.png" download>Tải PNG</a></div>
<div class="canvas"><div id="zz" style="transform-origin:0 0;width:{w:.0f}px">{svg}</div></div>
<h3>Dạng danh sách (để đọc / in)</h3><div class="tree card"><ul>{"".join(tree)}</ul></div></div>
<script>let s=1;function z(d){{s=d===0?1:Math.max(.3,Math.min(2,s+d));document.getElementById('zz').style.transform='scale('+s+')'}}
if(location.hash){{const el=document.getElementById(location.hash.slice(1));if(el)el.scrollIntoView({{block:'center'}})}}</script>
</body></html>"""
    (OUT / "phan_ra_chuc_nang.html").write_text(page, encoding="utf-8")


def write_dfd_page(rendered: dict) -> None:
    side = ['<div class="g">Mức khung cảnh &amp; mức 0</div>',
            '<a class="it" href="#CTX" data-d="CTX">Sơ đồ ngữ cảnh</a>', '<a class="it" href="#L0" data-d="L0">DFD mức 0</a>',
            '<div class="g">Mức 1 (từng phân hệ)</div>']
    for p in DFD_PHS:
        side.append(f'<a class="it" href="#L1-{p["code"]}" data-d="L1-{p["code"]}">{p["n"]}. {esc(p["name"])}</a>')
    side.append('<div class="g">Mức 2 (từng chức năng cấp 2)</div>')
    for p in DFD_PHS:
        gs = [g for g in p["groups"] if f"L2-{g}" in DIAGRAMS]
        if gs:
            side.append(f'<div class="sg">{p["n"]}. {esc(p["name"])}</div>')
            side += [f'<a class="it" href="#L2-{g}" data-d="L2-{g}">{g} {esc(GROUPS[g]["name"])}</a>' for g in gs]
    data = {}
    for did, d in DIAGRAMS.items():
        svg, w, h = rendered[did]
        rows = []
        for e in d["edges"]:
            rows.append({"s": node_title(e["s"]), "d": node_title(e["d"]), "kind": edge_kind(e),
                         "labels": e["labels"], "origins": [BY_FID[o]["id"] for o in e["origins"]]})
        bal = BALANCE.get(did)
        parent = None
        if d["level"] == 1:
            parent = {"t": "DFD mức 0", "href": "#L0"}
        elif d["level"] == 2:
            ph = GROUPS[d["parent"]]["ph"]
            parent = {"t": f"DFD mức 1 — {PH_BY_CODE[ph]['n']}. {PH_BY_CODE[ph]['name']}", "href": f"#L1-{ph}"}
        elif d["level"] == 0:
            parent = {"t": "Sơ đồ ngữ cảnh", "href": "#CTX"}
        procs = []
        for n in d["internal"]:
            num, name = proc_name(n[1])
            href = diagram_href(n[1])
            procs.append({"num": num, "name": name, "href": ("dfd.html" + href) if href.startswith("#") else href,
                          "deeper": href.startswith("#")})
        data[did] = {"title": d["title"], "svg": svg, "w": w, "rows": rows, "parent": parent, "procs": procs,
                     "bal": None if bal is None else {"ok": bal[0], "n": bal[1]}, "file": f"dfd/{did}.svg"}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>DFD các mức - {PROJECT['short']}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>{BASE_CSS}
.canvas{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:auto;margin:10px 0}}
.bar{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:13px}}.bar button{{border:1px solid #cbd5e1;background:#fff;
border-radius:7px;padding:4px 10px;cursor:pointer}}.hide-audit .audit{{display:none}}.bc{{font-size:13px;margin-bottom:6px}}
.k{{display:inline-block;width:26px;height:0;border-top:2px solid;vertical-align:middle;margin-right:4px}}
</style></head><body>{nav_html("dfd.html")}<div class="lay"><aside>{"".join(side)}</aside><main>
<div class="bc" id="bc"></div><h1 id="ttl"></h1>
<div class="sbt">Ký hiệu giáo trình PTTK: tiến trình = hình tròn có số hiệu, kho = hai đường song song có mã kho, tác nhân = hình chữ nhật,
luồng = mũi tên có tên (luồng vào/ra kho không đặt tên vì mang cả bản ghi). Luồng chỉ được khai báo ở <b>mức lá</b> và được
<b>gộp lên</b> mức trên, nên các mức luôn cân bằng. Mọi tiến trình đều qua kiểm tra token + phân quyền (1.3.2) — không vẽ để sơ đồ gọn.</div>
<div class="bar" style="margin-top:10px"><span id="bal"></span>
<label><input type="checkbox" id="aud" checked onchange="aud()"> hiện luồng ghi vết nhật ký</label>
<span>Phóng to: <button onclick="z(-.1)">−</button> <button onclick="z(0)">100%</button> <button onclick="z(.1)">+</button></span>
<a id="dl" download>Tải SVG</a><a id="dlp" download>Tải PNG</a></div>
<div class="canvas" id="cv"><div id="zz" style="transform-origin:0 0"></div></div>
<div id="procs"></div>
<h3>Bảng luồng dữ liệu của sơ đồ (từ điển luồng)</h3><table id="tb"></table></main></div>
<script>
const D={payload};
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
let cur='L0',sc=1;
const KN={{data:'dữ liệu',read:'đọc kho',write:'ghi kho',event:'sự kiện',audit:'ghi vết'}};
const KC={{data:'#334155',read:'#2563eb',write:'#ea580c',event:'#db2777',audit:'#94a3b8'}};
function show(id){{if(!D[id])id='L0';cur=id;const d=D[id];
document.querySelectorAll('aside a.it').forEach(a=>a.classList.toggle('on',a.dataset.d===id));
document.getElementById('ttl').textContent=d.title;
document.getElementById('bc').innerHTML=d.parent?`Mức trên: <a href="${{d.parent.href}}">${{esc(d.parent.t)}}</a>`:'Mức cao nhất';
document.getElementById('bal').innerHTML=d.bal?(d.bal.ok?`<span class="pill ok">✓ cân bằng với tiến trình mức trên (${{d.bal.n}} luồng ngoài khớp)</span>`:`<span class="pill bad">✗ lệch với mức trên</span>`):'';
document.getElementById('zz').innerHTML=d.svg;sc=1;z(0);
document.getElementById('dl').href=d.file;document.getElementById('dlp').href=d.file.replace('.svg','.png');
document.getElementById('procs').innerHTML=d.procs.length>1||id==='CTX'?'<h3>Tiến trình trong sơ đồ</h3>'+d.procs.map(p=>`<span class="pill unk">${{esc(p.num)}}</span> <a href="${{p.href}}">${{esc(p.name)}}</a> <span class="muted">${{p.deeper?'→ sơ đồ mức sâu hơn':'→ đặc tả chức năng lá'}}</span>`).join('<br>'):'';
let h='<tr><th>#</th><th>Từ</th><th>Đến</th><th>Dữ liệu</th><th>Loại</th><th>Phân rã từ chức năng lá</th></tr>';
d.rows.forEach((r,i)=>{{h+=`<tr><td>${{i+1}}</td><td>${{esc(r.s)}}</td><td>${{esc(r.d)}}</td><td>${{r.labels.length?r.labels.map(esc).join('<br>'):'<i class=muted>(cả bản ghi)</i>'}}</td><td><span class="k" style="border-color:${{KC[r.kind]||'#334155'}}"></span>${{KN[r.kind]||r.kind}}</td><td>${{r.origins.map(o=>`<a href="dac_ta_chuc_nang.html#${{o}}">${{o}}</a>`).join(', ')}}</td></tr>`}});
document.getElementById('tb').innerHTML=h;aud();window.scrollTo(0,0)}}
function z(d){{sc=d===0?1:Math.max(.3,Math.min(2.2,sc+d));document.getElementById('zz').style.transform='scale('+sc+')';
document.getElementById('zz').style.width=(D[cur].w*sc)+'px'}}
function aud(){{document.getElementById('cv').classList.toggle('hide-audit',!document.getElementById('aud').checked)}}
window.addEventListener('hashchange',()=>show(location.hash.slice(1)));show(location.hash.slice(1)||'L0');
</script></body></html>"""
    (OUT / "dfd.html").write_text(page, encoding="utf-8")


def write_spec_page(leaves_json: list[dict]) -> None:
    side = ['<input id="q" placeholder="Tìm chức năng, bảng, endpoint…" oninput="side()" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:8px">',
            '<select id="ent" onchange="side()" style="width:100%;margin-top:6px;padding:6px;border:1px solid #cbd5e1;border-radius:8px">'
            '<option value="">Mọi tác nhân</option>' + "".join(f'<option value="{c}">{esc(n)}</option>' for c, n, *_ in P.ENTITIES) + "</select>",
            '<a class="it" href="#" data-id="">▸ Ma trận truy vết (tổng quan)</a><div id="tree"></div>']
    meta = {"phs": [{"code": p["code"], "n": p["n"], "name": p["name"], "color": p["color"],
                     "groups": [{"id": g, "name": GROUPS[g]["name"], "leaves": GROUPS[g]["leaves"]} for g in p["groups"]]} for p in PHS],
            "tables": {t: TABLE_TITLE[t] for t in TABLES}, "stores": {k: v for k, v in STORE_NAME.items()}}
    payload = json.dumps({"L": leaves_json, "M": meta}, ensure_ascii=False).replace("</", "<\\/")
    page = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Đặc tả &amp; truy vết - {PROJECT['short']}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>{BASE_CSS}
.hd{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}.lay2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
@media(max-width:1100px){{.lay2{{grid-template-columns:1fr}}}}ol.xl li{{margin:4px 0;font-size:13.4px}}
.tree ul{{list-style:none;margin:2px 0;padding-left:16px;border-left:2px solid #e2e8f0}}.tree li{{margin:2px 0;font-size:12.5px}}
.ly{{display:inline-block;min-width:74px;text-align:center;font-size:10.5px;font-weight:800;border-radius:5px;padding:0 5px;margin-right:6px}}
.ly-controller{{background:#e0e7ff;color:#3730a3}}.ly-service{{background:#dcfce7;color:#166534}}.ly-repository{{background:#fef3c7;color:#92400e}}
.ly-core{{background:#f3e8ff;color:#6b21a8}}.ly-job{{background:#fce7f3;color:#9d174d}}.mx td{{font-size:12px}}.mx td:nth-child(2){{min-width:220px}}
.code{{font-family:Consolas,monospace;font-size:12.2px}}.note{{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:8px 12px;font-size:13px}}
</style></head><body>{nav_html("dac_ta_chuc_nang.html")}<div class="lay"><aside>{"".join(side)}</aside><main id="main"></main></div>
<script>
const {{L,M}}={payload};
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;');
const BY=Object.fromEntries(L.map(l=>[l.id,l]));
const KIND={{api:'API',job:'Tác vụ nền',internal:'Xử lý nội bộ',client:'Phía client'}};
const st=s=>s==='passed'?'<span class="pill ok">đạt</span>':s==='failed'?'<span class="pill bad">lỗi</span>':'<span class="pill unk">?</span>';
const tb=(t,m)=>`<a class="pill ${{m==='R'?'pr':m==='W'?'pw':'prw'}}" href="csdl_chi_tiet.html#${{t}}" title="${{esc(M.tables[t]||t)}}">${{t}} · ${{m==='R'?'đọc':m==='W'?'ghi':'đọc+ghi'}}</a>`;
function match(l){{const q=document.getElementById('q').value.toLowerCase().trim();const e=document.getElementById('ent').value;
if(e&&!l.ents.some(x=>x.id===e))return false;if(!q)return true;
return (l.id+' '+l.fid+' '+l.name+' '+l.R.join(' ')+' '+l.W.join(' ')+' '+l.RW.join(' ')+' '+l.routes.map(r=>r.key).join(' ')).toLowerCase().includes(q)}}
function side(){{let h='';const cur=location.hash.slice(1);
M.phs.forEach(p=>{{let inner='';p.groups.forEach(g=>{{const ls=g.leaves.map(id=>BY[id]).filter(match);if(!ls.length)return;
inner+=`<div class="sg">${{g.id}} ${{esc(g.name)}}</div>`+ls.map(l=>`<a class="it ${{l.id===cur?'on':''}}" href="#${{l.id}}">${{l.id}} ${{esc(l.name)}}</a>`).join('')}});
if(inner)h+=`<div class="g" style="color:${{p.color}}">${{p.n}}. ${{esc(p.name)}}</div>`+inner}});
document.getElementById('tree').innerHTML=h||'<p class="muted">Không có chức năng phù hợp</p>';
if(!cur)matrix()}}
function chain(n){{return `<li><span class="ly ly-${{n.layer}}">${{n.layer}}</span><a class="code" href="${{n.href}}" target="_blank">${{esc(n.fn)}}</a>${{n.rec?' <i class=muted>(đệ quy)</i>':''}}`+(n.c.length?'<ul>'+n.c.map(chain).join('')+'</ul>':'')+'</li>'}}
function errs(es){{if(!es.length)return '<p class="muted">Không có lỗi nghiệp vụ.</p>';
return '<table><tr><th>HTTP</th><th>Thông điệp (detail)</th><th>Phát sinh tại</th></tr>'+es.map(e=>`<tr><td><b>${{e.status??''}}</b></td><td>${{esc(e.msg)}}</td><td><a class="code" href="${{e.href}}" target="_blank">${{esc(e.at)}}</a></td></tr>`).join('')+'</table>'}}
function fields(r){{let h='';if(r.params.length)h+='<table><tr><th>Tham số</th><th>Vị trí</th><th>Kiểu</th><th>Bắt buộc</th></tr>'+r.params.map(p=>`<tr><td><code>${{esc(p.name)}}</code></td><td>${{p.in}}</td><td>${{esc(p.type)}}</td><td>${{p.required?'có':''}}</td></tr>`).join('')+'</table>';
if(r.body)h+=`<p>Thân yêu cầu: <code>${{esc(r.body.content)}}</code> ${{r.body.schema?'<code>'+esc(r.body.schema)+'</code>':''}}</p><table><tr><th>Trường</th><th>Kiểu</th><th>Bắt buộc</th></tr>`+r.body.fields.map(f=>`<tr><td><code>${{esc(f.name)}}</code></td><td>${{esc(f.type)}}</td><td>${{f.required?'có':''}}</td></tr>`).join('')+'</table>';
h+=`<p>Phản hồi: <code>${{esc(r.response)}}</code></p>`;return h}}
function node(n){{return n.t==='P'?`<a href="${{n.href}}">${{n.id}} ${{esc(n.name)}}</a>`:n.t==='S'?(n.href?`<a href="${{n.href}}">${{n.id}} ${{esc(n.name)}}</a>`:`${{n.id}} ${{esc(n.name)}}`):`<a href="?tac_nhan=${{n.id}}">${{esc(n.name)}}</a>`}}
function show(id){{const l=BY[id];if(!l){{matrix();return}}
let h=`<div class="card"><div class="hd"><span class="tag" style="background:${{l.color}}">${{l.phn}}. ${{esc(l.phname)}}</span><span class="muted">›</span>
<a href="${{l.ghref}}">${{l.group}} ${{esc(l.gname)}}</a><span class="muted">›</span><h1>${{l.id}} ${{esc(l.name)}}</h1></div>
<p class="muted">Mã tính năng <b>${{l.fid}}</b> · loại: <b>${{KIND[l.kind]}}</b>${{l.screen?' · màn hình: <b>'+esc(l.screen)+'</b>':''}}${{l.change?' · thay đổi so với bản gốc: '+esc(l.change):''}}</p>
<p>Tác nhân: ${{l.ents.length?l.ents.map(e=>`<a class="pill unk" href="?tac_nhan=${{e.id}}">${{esc(e.name)}}</a>`).join(''):'<i>hệ thống (không có tác nhân ngoài)</i>'}}
${{l.roles.length?'<br>Vai trò được dùng (từ code: require_roles / phạm vi): '+l.roles.map(esc).join(', '):''}}</p>
${{l.note?'<p class="note">Ghi chú truy vết: '+esc(l.note)+'</p>':''}}</div>`;
h+=`<div class="lay2"><div class="card"><h3>Đầu vào / đầu ra (nghiệp vụ)</h3><p><b>Vào:</b> ${{esc(l.vao)||'<i class=muted>— (kích hoạt nội bộ)</i>'}}<br><b>Ra:</b> ${{esc(l.ra)||'<i class=muted>—</i>'}}</p>
<h3>Xử lý</h3><ol class="xl">${{l.xl.map(x=>'<li>'+esc(x)+'</li>').join('')}}</ol></div>
<div class="card"><h3>Kho dữ liệu (đo khi chạy 279 test)</h3><p>${{l.R.map(t=>tb(t,'R')).join('')}}${{l.W.map(t=>tb(t,'W')).join('')}}${{l.RW.map(t=>tb(t,'RW')).join('')}}${{!(l.R.length+l.W.length+l.RW.length)?'<i class=muted>Không đọc/ghi bảng CSDL</i>':''}}</p>
<p>Kho DFD: ${{[...l.stores.R.map(s=>s+' (đọc)'),...l.stores.W.map(s=>s+' (ghi)')].map(esc).join(', ')||'—'}}</p>
${{l.redirects.length?'<p>Ghi gián tiếp qua trình nghe sự kiện → '+l.redirects.map(r=>`<a href="#${{r.to}}">${{r.to}}</a> (${{esc(r.label)}}, bảng <code>${{r.table}}</code>)`).join('; ')+'</p>':''}}
<h3>Luồng dữ liệu mức lá</h3><table><tr><th>Từ</th><th>Đến</th><th>Dữ liệu</th></tr>${{l.flows.map(f=>`<tr><td>${{node(f.s)}}</td><td>${{node(f.d)}}</td><td>${{esc(f.label)||'<i class=muted>'+(f.kind==='read'?'đọc':'ghi')+'</i>'}}</td></tr>`).join('')}}</table></div></div>`;
l.routes.forEach(r=>{{h+=`<div class="card"><h3>API <code>${{esc(r.key)}}</code></h3><p class="muted">${{esc(r.summary)}}${{r.doc?' — '+esc(r.doc):''}}</p>
<p>Quyền: <b>${{r.auth==='roles'?'chỉ '+r.roles.map(esc).join(', '):r.auth==='login'?'mọi tài khoản đã đăng nhập (phạm vi kiểm trong service)':'không cần đăng nhập'}}</b></p>${{fields(r)}}
<div class="lay2"><div><h3>Chuỗi gọi (controller → service → repository)</h3><div class="tree"><ul>${{chain(r.chain)}}</ul></div></div>
<div><h3>Lỗi có thể trả về</h3>${{errs(r.errors)}}<h3>Bảng đọc/ghi khi chạy</h3><p>${{r.sql.R.map(t=>tb(t,'R')).join('')}}${{r.sql.W.map(t=>tb(t,'W')).join('')}}</p>
${{Object.entries(r.sql_other).map(([k,v])=>`<p class="muted">${{({{ok_auth:'Qua xác thực / phân quyền',ok_notify:'Qua trình nghe sinh thông báo (7.1.1)',ok_audit:'Qua ghi nhật ký (9.1.x)'}})[k]}}: ${{['R','W'].flatMap(m=>(v[m]||[]).map(t=>t+(m==='R'?' (đọc)':' (ghi)'))).join(', ')}}</p>`).join('')}}
<h3>Phía client</h3>${{r.api_methods.length?'<p>Hàm API: '+r.api_methods.map(m=>`<a class="code" href="${{m.href}}" target="_blank">${{esc(m.call)}}</a>`).join(', ')+'</p>':''}}
${{r.client.length?'<table><tr><th>Nơi gọi</th><th>Màn hình (route)</th></tr>'+r.client.map(c=>`<tr><td><a class="code" href="${{c.href}}" target="_blank">${{esc(c.file)}}</a> · ${{esc(c.call)}}</td><td>${{c.screens.map(esc).join(', ')||'<i class=muted>dùng chung</i>'}}</td></tr>`).join('')+'</table>':'<p class="muted">Không có màn hình nào gọi endpoint này.</p>'}}</div></div></div>`}});
l.jobs.forEach(j=>{{h+=`<div class="card"><h3>Tác vụ nền <code>${{esc(j.key)}}</code></h3><p>Vòng lặp: <a class="code" href="${{j.loop_href}}" target="_blank">${{esc(j.loop)}}</a> — ${{esc(j.doc)}}</p>
<div class="lay2"><div><h3>Chuỗi gọi</h3><div class="tree"><ul>${{chain(j.chain)}}</ul></div></div><div><h3>Lỗi</h3>${{errs(j.errors)}}<h3>Bảng đọc/ghi khi chạy</h3><p>${{j.sql.R.map(t=>tb(t,'R')).join('')}}${{j.sql.W.map(t=>tb(t,'W')).join('')}}</p></div></div></div>`}});
if(l.fns.length||l.files.length)h+=`<div class="card"><h3>Mã nguồn</h3>${{l.fns.map(f=>`<p><a class="code" href="${{f.href}}" target="_blank">${{esc(f.fn)}}</a> — ${{esc(f.doc)}}${{f.errors.length?'<br>'+f.errors.map(e=>`<span class="pill unk">${{e.status}}</span> ${{esc(e.msg)}}`).join(' · '):''}}</p>`).join('')}}${{l.files.map(f=>`<p><a class="code" href="${{f.href}}" target="_blank">${{esc(f.f)}}</a></p>`).join('')}}</div>`;
h+=`<div class="lay2"><div class="card"><h3>Kiểm thử</h3>${{l.tests.length?'<table><tr><th>Test</th><th>Kết quả</th><th>Nguồn</th></tr>'+l.tests.map(t=>`<tr><td><a class="code" href="${{t.href}}" target="_blank">${{esc(t.name)}}</a></td><td>${{st(t.status)}}</td><td class="muted">${{t.origin}}</td></tr>`).join('')+'</table>':'<p class="muted">Chưa có test riêng.</p>'}}
${{l.tests_total>10?`<p class="muted">Tổng ${{l.tests_total}} test gọi tới chức năng này khi chạy; hiện 10 test tiêu biểu.</p>`:''}}</div>
<div class="card"><h3>Xuất hiện trong</h3>${{l.used.map(u=>`<a href="${{u.href}}">${{esc(u.t)}}</a>`).join('<br>')}}</div></div>`;
document.getElementById('main').innerHTML=h;side();window.scrollTo(0,0)}}
function matrix(){{const e=new URLSearchParams(location.search).get('tac_nhan');if(e)document.getElementById('ent').value=e;
const ls=L.filter(match);let h=`<h1>Ma trận truy vết</h1><div class="sbt">${{ls.length}} / ${{L.length}} chức năng lá${{e?' · tác nhân: '+esc((L.flatMap(l=>l.ents).find(x=>x.id===e)||{{}}).name||e):''}}.
Mỗi dòng nối: chức năng lá ↔ endpoint ↔ bảng CSDL (đo khi chạy) ↔ màn hình client ↔ test. Bấm mã để xem đặc tả đầy đủ.</div>
<table class="mx"><tr><th>Mã</th><th>Chức năng lá</th><th>Tác nhân</th><th>Endpoint / tác vụ</th><th>Bảng (đ: đọc, g: ghi)</th><th>Màn hình</th><th>Test</th></tr>`;
ls.forEach(l=>{{const scr=[...new Set(l.routes.flatMap(r=>r.client.flatMap(c=>c.screens)))];
h+=`<tr><td><a href="#${{l.id}}"><b>${{l.id}}</b></a><br><span class="muted">${{l.fid}}</span></td><td>${{esc(l.name)}}</td><td>${{l.ents.map(x=>esc(x.name)).join(', ')||'<i class=muted>hệ thống</i>'}}</td>
<td class="code">${{[...l.routes.map(r=>esc(r.key)),...l.jobs.map(j=>esc(j.key)),...l.fns.map(f=>esc(f.fn)),...l.files.map(f=>esc(f.f))].join('<br>')}}</td>
<td>${{[...l.R.map(t=>t+' (đ)'),...l.W.map(t=>t+' (g)'),...l.RW.map(t=>t+' (đ+g)')].join('<br>')}}</td><td>${{scr.map(esc).join('<br>')||l.screen&&esc(l.screen)||''}}</td>
<td>${{l.tests.filter(t=>t.status==='passed').length}}/${{l.tests.length}}${{l.tests_total>l.tests.length?' (gọi bởi '+l.tests_total+')':''}}</td></tr>`}});
document.getElementById('main').innerHTML=h+'</table>'}}
window.addEventListener('hashchange',()=>show(location.hash.slice(1)));
side();if(location.hash.slice(1))show(location.hash.slice(1));
</script></body></html>"""
    (OUT / "dac_ta_chuc_nang.html").write_text(page, encoding="utf-8")


def write_index() -> None:
    idx = {"leaves": [{"id": lf["id"], "fid": lf["fid"], "name": lf["name"], "ph": lf["ph"], "group": lf["group"],
                       "R": lf["R"], "W": lf["W"], "RW": lf["RW"], "roles": lf["roles"], "vao": lf.get("vao", ""),
                       "ra": lf.get("ra", ""), "readonly": lf["readonly"], "kind": lf["kind"]} for lf in LEAVES],
           "phs": [{"code": p["code"], "n": p["n"], "name": p["name"], "groups": p["groups"], "dfd": p["dfd"]} for p in PHS],
           "groups": {g: {"name": v["name"], "ph": v["ph"], "leaves": v["leaves"]} for g, v in GROUPS.items()},
           "diagrams": list(DIAGRAMS), "nav": NAV}
    (TRACE / "leaf_index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")


# ============================================================================ main
def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dfd").mkdir(exist_ok=True)
    rendered = {}
    for did, d in DIAGRAMS.items():
        svg, w, h = render(d)
        rendered[did] = (svg, w, h)
        (OUT / "dfd" / f"{did}.svg").write_text(svg, encoding="utf-8")
    bfd, bw, bh = render_bfd()
    (OUT / "phan_ra_chuc_nang.svg").write_text(bfd, encoding="utf-8")
    write_bfd_page(bfd, bw)
    write_dfd_page(rendered)
    write_spec_page([leaf_json(lf) for lf in LEAVES])
    write_index()
    import gen_chuan_hoa
    gen_chuan_hoa.write(OUT, BASE_CSS, nav_html("chuan_hoa_csdl.html"))

    print(f"phan he {len(PHS)} | chuc nang cap 2 {len(GROUPS)} | chuc nang la {len(LEAVES)} | luong muc la {len(FLOWS_LEAF)} "
          f"| so do DFD {len(DIAGRAMS)}")
    for m in checks():
        print(" -", m)

    if "--png" in sys.argv or "--png-all" in sys.argv:
        import gen_so_do_csdl as G
        G.svg_to_png(OUT / "phan_ra_chuc_nang.svg", OUT / "phan_ra_chuc_nang.png", int(bw), int(bh), 1.25)
        for did, (_svg, w, h) in rendered.items():
            if "--png-all" in sys.argv or not did.startswith("L2-"):
                G.svg_to_png(OUT / "dfd" / f"{did}.svg", OUT / "dfd" / f"{did}.png", int(w), int(h), 1.5)
        print("da xuat PNG")

    # Gan lien ket vao 4 trang cu
    import gen_so_do_csdl as G
    G.main()


if __name__ == "__main__":
    main()
