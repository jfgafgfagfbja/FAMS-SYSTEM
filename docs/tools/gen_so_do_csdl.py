"""Sinh bo "So do luong du lieu va CSDL" cua FAMS -> docs/so-do-luong-du-lieu-va-csdl/.

    server/venv/Scripts/python docs/tools/gen_so_do_csdl.py [--png]

- Cau truc bang (cot, kieu, khoa, quan he, chi muc) doc truc tiep tu server/app/db/models.py.
- Noi dung tieng Viet (mo ta, quy trinh, cay chuc nang): docs/tools/so_do_data.py.
- Giao dien: docs/tools/so_do_templates/ (tach tu bo goc bang make_so_do_templates.py).
- --png: xuat erd.png tu erd.svg bang Edge/Chrome chay an (khong dung ho so trinh duyet cua nguoi dung).
"""
import html
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from sqlalchemy import Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(TOOLS))

from app.db import models  # noqa: E402,F401
from app.db.database import Base  # noqa: E402
from so_do_data import FLOWS, GROUPS, PROJECT, ROLES, STORES, TABLES  # noqa: E402

OUT = ROOT / "docs" / "so-do-luong-du-lieu-va-csdl"
TPL = TOOLS / "so_do_templates"
# Chi muc chuc nang la do gen_phan_ra.py sinh: neu co, 4 trang nay duoc gan lien ket sang
# Phan ra chuc nang / DFD / Dac ta & truy vet (va cay chuc nang dung lai tu quyen thuc trong code).
_IDX = TOOLS / "trace" / "leaf_index.json"
LEAF_INDEX = json.loads(_IDX.read_text(encoding="utf-8")) if _IDX.exists() else None
PG = postgresql.dialect()
META = {t.name: t for t in Base.metadata.sorted_tables}
ORDER = [name for _g, _c, names in GROUPS for name in names]
GROUP_OF = {name: (g, c) for g, c, names in GROUPS for name in names}
STORE_OF = {name: code for code, _n, names in STORES for name in names}
MODEL_OF = {m.class_.__tablename__: m.class_.__name__ for m in Base.registry.mappers}


def check_data() -> None:
    """Moi bang/cot trong models phai co mo ta, va nguoc lai - tranh tai lieu lech code."""
    errors = []
    if set(META) != set(TABLES):
        errors.append(f"bang thieu mo ta: {sorted(set(META) - set(TABLES))}; mo ta thua: {sorted(set(TABLES) - set(META))}")
    if sorted(ORDER) != sorted(META):
        errors.append("GROUPS khong phu kin 21 bang")
    for name, table in META.items():
        cols = {c.name for c in table.columns}
        desc = set(TABLES.get(name, {}).get("cols", {}))
        if cols != desc:
            errors.append(f"{name}: cot thieu mo ta {sorted(cols - desc)}, mo ta thua {sorted(desc - cols)}")
    for flow in FLOWS:
        for step in flow["steps"]:
            for item in step["db"] + step.get("no", {}).get("db", []):
                rw, table = item.split(":")
                if rw not in ("R", "W") or table not in META:
                    errors.append(f"quy trinh {flow['key']}: tham chieu sai '{item}'")
    if errors:
        raise SystemExit("Du lieu tai lieu lech voi models:\n  " + "\n  ".join(errors))


# ----------------------------------------------------------------------------- cot, khoa
def col_type(col) -> str:
    return col.type.compile(dialect=PG)


def unique_single(table) -> set[str]:
    names = {c.name for c in table.columns if c.unique}
    for con in table.constraints:
        if con.__class__.__name__ == "UniqueConstraint" and len(con.columns) == 1:
            names.update(c.name for c in con.columns)
    return names


def col_keys(table, col) -> str:
    keys = []
    if col.primary_key:
        keys.append("PK")
    for fk in col.foreign_keys:
        keys.append(f"FK:{fk.column.table.name}")
    if col.name in unique_single(table) and not col.primary_key:
        keys.append("UQ")
    if not col.nullable and not col.primary_key:
        keys.append("NN")
    return " ".join(keys)


def composite_constraints(table) -> list[str]:
    out = []
    for con in table.constraints:
        if con.__class__.__name__ == "UniqueConstraint" and len(con.columns) > 1:
            out.append("UNIQUE (" + ", ".join(c.name for c in con.columns) + ")")
    return out


def fk_out(table) -> list[list]:
    return [[c.name, fk.column.table.name, bool(c.nullable)] for c in table.columns for fk in c.foreign_keys]


def fk_in(name: str) -> list[list]:
    rows = []
    for other in ORDER:
        for c in META[other].columns:
            for fk in c.foreign_keys:
                if fk.column.table.name == name:
                    rows.append([other, c.name])
    return rows


# ----------------------------------------------------------------------------- schema.sql
def sql_str(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def table_ddl(name: str) -> str:
    table = META[name]
    doc = TABLES[name]
    raw = str(CreateTable(table).compile(dialect=PG)).strip()
    lines = raw.splitlines()
    out = [lines[0].replace("CREATE TABLE ", "CREATE TABLE ")]
    body = [line.strip().rstrip(",").rstrip() for line in lines[1:-1]]
    for i, line in enumerate(body):
        comma = "," if i < len(body) - 1 else ""
        first = line.split(" ", 1)[0]
        note = doc["cols"].get(first)
        out.append(f"  {line}{comma}" + (f"  -- {note}" if note else ""))
    out.append(");")
    for idx in sorted(table.indexes, key=lambda i: i.name):
        out.append(str(CreateIndex(idx).compile(dialect=PG)).strip() + ";")
    out.append(f"COMMENT ON TABLE {name} IS {sql_str(doc['title'] + ': ' + doc['desc'])};")
    for col in table.columns:
        out.append(f"COMMENT ON COLUMN {name}.{col.name} IS {sql_str(doc['cols'][col.name])};")
    return "\n".join(out)


def alembic_head() -> str:
    """Revision head: revision khong bi migration nao khac tro toi qua down_revision."""
    import re
    revs, downs = set(), set()
    for f in (ROOT / "server" / "alembic" / "versions").glob("*.py"):
        text = f.read_text(encoding="utf-8")
        m = re.search(r"""^revision\s*(?::\s*str)?\s*=\s*["']([0-9a-f]+)["']""", text, re.M)
        if m:
            revs.add(m.group(1))
        downs.update(re.findall(r"""^down_revision[^=]*=\s*["']([0-9a-f]+)["']""", text, re.M))
    heads = sorted(revs - downs)
    return ", ".join(heads) or "?"


def build_schema_sql() -> str:
    head = [
        "-- =====================================================================",
        f"-- CSDL: {PROJECT['name'].upper()} (PostgreSQL 16 + pgvector)",
        f"-- {len(META)} bảng. Sinh tự động từ server/app/db/models.py (docs/tools/gen_so_do_csdl.py).",
        f"-- Môi trường thật tạo / nâng cấp schema bằng Alembic (server/alembic, head {alembic_head()});",
        "-- tệp này dùng để đọc, đưa vào báo cáo hoặc dựng CSDL thử nghiệm.",
        "-- =====================================================================",
        "-- CREATE DATABASE fams_system ENCODING 'UTF8';  -- \\c fams_system",
        "CREATE EXTENSION IF NOT EXISTS vector;",
        "",
    ]
    parts = []
    for t in Base.metadata.sorted_tables:  # thu tu phu thuoc khoa ngoai
        g, _c = GROUP_OF[t.name]
        parts.append(f"-- ---------------------------------------------------------------- {t.name} ({TABLES[t.name]['title']} · {g})")
        parts.append(table_ddl(t.name))
        parts.append("")
    return "\n".join(head + parts)


# ----------------------------------------------------------------------------- du lieu trang
def used_by_flows(name: str) -> list[list[str]]:
    rows = []
    for flow in FLOWS:
        if not flow["func"] or flow["key"] == "master":
            continue
        rw = set()
        for step in flow["steps"]:
            for item in step["db"] + step.get("no", {}).get("db", []):
                kind, table = item.split(":")
                if table == name:
                    rw.add(kind)
        if rw:
            rows.append([flow["tab"], "".join(sorted(rw))])
    return rows


def build_tb() -> list[dict]:
    out = []
    for name in ORDER:
        table = META[name]
        doc = TABLES[name]
        group, color = GROUP_OF[name]
        model = MODEL_OF[name]
        out.append({
            "vn": name, "en": f"models.{model}", "title": doc["title"], "group": group, "color": color,
            "desc": html.escape(doc["desc"]), "store": STORE_OF.get(name, "—"),
            "cols": [[c.name, f"{model}.{c.name}", col_type(c), col_keys(table, c), html.escape(doc["cols"][c.name])]
                     for c in table.columns],
            "cons": composite_constraints(table), "fkOut": fk_out(table), "fkIn": fk_in(name),
            "used": used_by_flows(name), "ddl": table_ddl(name), "leaves": leaves_using(name),
        })
    return out


def leaves_using(name: str) -> list[list[str]]:
    """[ma la, ten, R|W|RW] cac chuc nang la doc/ghi bang (do khi chay test) - tu leaf_index.json."""
    if not LEAF_INDEX:
        return []
    out = []
    for lf in LEAF_INDEX["leaves"]:
        mode = "RW" if name in lf["RW"] else "W" if name in lf["W"] else "R" if name in lf["R"] else ""
        if mode:
            out.append([lf["id"], lf["name"], mode])
    return out


def tint(hex_color: str) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(round(v + (255 - v) * 0.9) for v in (r, g, b))


def build_roles() -> list[dict]:
    if LEAF_INDEX:
        return build_roles_from_leaves()
    return [{**r, "tint": tint(r["color"]), "groups": [
        {"menu": g["menu"], "readonly": g.get("readonly", False),
         "rows": [[html.escape(x) for x in row] for row in g["rows"]]} for g in r["groups"]]} for r in ROLES]


def build_roles_from_leaves() -> list[dict]:
    """Cay chuc nang theo vai tro DUNG LAI tu phan ra + quyen thuc trong code (require_roles / pham vi):
    vai tro -> phan he (menu) -> chuc nang la (lien ket dac ta) + du lieu vao/ra."""
    out = []
    for r in ROLES:
        groups = []
        for ph in LEAF_INDEX["phs"]:
            if not ph["dfd"]:
                continue
            leaves = [lf for lf in LEAF_INDEX["leaves"] if lf["ph"] == ph["code"] and r["role"] in lf["roles"]]
            if not leaves:
                continue
            rows = [[f'<a href="dac_ta_chuc_nang.html#{lf["id"]}" style="font-weight:800;color:#0E9594;text-decoration:none">{lf["id"]}</a> '
                     f'{html.escape(lf["name"])}', html.escape(lf["vao"] or "—"), html.escape(lf["ra"] or "—")]
                    for lf in leaves]
            groups.append({"menu": f'{ph["n"]}. {ph["name"]}', "readonly": all(lf["readonly"] for lf in leaves),
                           "rows": rows})
        out.append({**{k: r[k] for k in ("id", "name", "role", "color", "letter", "desc")},
                    "tint": tint(r["color"]), "groups": groups})
    return out


NEW_NAV = [("workflow_tong_quan.html", "Sơ đồ quy trình"), ("erd_csdl.html", "CSDL (ERD)"),
           ("csdl_chi_tiet.html", "Chi tiết từng bảng CSDL"), ("chuc_nang_cay.html", "Sơ đồ chức năng cây"),
           ("phan_ra_chuc_nang.html", "Phân rã chức năng"), ("dfd.html", "DFD các mức"),
           ("dac_ta_chuc_nang.html", "Đặc tả & truy vết"), ("chuan_hoa_csdl.html", "Chuẩn hóa CSDL (4NF)")]


def patch_template(template: str, text: str) -> str:
    """Gan lien ket sang bo phan ra / DFD / dac ta (chi khi da co leaf_index.json)."""
    if not LEAF_INDEX:
        return text
    import re
    nav = '<nav class="top">' + "".join(
        f'<a href="{h}" class="{"on" if h == template else ""}">{t}</a>' for h, t in NEW_NAV) + "</nav>"
    if '<nav class="top">' in text:
        text = re.sub(r'<nav class="top">.*?</nav>', nav, text, count=1, flags=re.S)
    else:  # cay chuc nang: chua co thanh dieu huong tren cung
        css = ('<style>nav.top{display:flex;flex-direction:row;align-items:center;gap:6px;flex-wrap:wrap;padding:10px 24px;background:#0f2a3d;position:relative;z-index:9}'
               'nav.top a{color:#cbd5e1;text-decoration:none;font-size:13px;font-weight:600;padding:7px 14px;border-radius:8px;'
               'font-family:"Segoe UI",system-ui,sans-serif}nav.top a:hover{background:rgba(255,255,255,.1)}'
               'nav.top a.on{background:#0e9594;color:#fff}</style>')
        text = text.replace("<body>", "<body>" + css + nav, 1)
    if template == "csdl_chi_tiet.html":
        anchor = "h+='<h3>Câu lệnh tạo bảng ({{DBMS}})</h3>"
        add = ("h+='<h3>Chức năng lá đọc / ghi bảng này (đo khi chạy 279 test)</h3>'+(t.leaves.length?t.leaves.map(l=>"
               "`<a class=\"u\" style=\"text-decoration:none;color:#0c4a6e\" href=\"dac_ta_chuc_nang.html#${l[0]}\"><b>${l[0]}</b> ${l[1]} · "
               "${l[2]==='R'?'đọc':l[2]==='W'?'ghi':'đọc + ghi'}</a>`).join(''):'<i>Không có chức năng nào</i>');")
        assert anchor in text, "csdl_chi_tiet: doi mau?"
        text = text.replace(anchor, add + anchor, 1)
    if template == "workflow_tong_quan.html":
        a1 = "document.getElementById('dsc').textContent = f.desc;"
        a2 = '<p id="dsc"></p>'
        assert a1 in text and a2 in text, "workflow: doi mau?"
        text = text.replace(a1, a1 + " document.getElementById('lnk').innerHTML = f.links || '';", 1)
        text = text.replace(a2, a2 + '<p id="lnk" style="margin:6px 0 0;font-size:13px"></p>', 1)
    if template == "chuc_nang_cay.html":
        text = text.replace("</script>\n</body>", "if(location.hash) selectTab(location.hash.slice(1));\n"
                            "window.addEventListener('hashchange',()=>selectTab(location.hash.slice(1)));\n</script>\n</body>", 1)
    return text


def flow_links(flow: dict) -> str:
    if not LEAF_INDEX:
        return ""
    key = flow["key"]
    if key == "master":
        return ('Phân rã chi tiết: <a href="dfd.html#CTX">Sơ đồ ngữ cảnh</a> · <a href="dfd.html#L0">DFD mức 0</a> · '
                '<a href="phan_ra_chuc_nang.html">Sơ đồ phân rã chức năng</a> · <a href="dac_ta_chuc_nang.html">Ma trận truy vết</a>')
    ph = next((p for p in LEAF_INDEX["phs"] if p["code"].lower() == key), None)
    if ph:
        n_leaf = sum(len(LEAF_INDEX["groups"][g]["leaves"]) for g in ph["groups"])
        first = LEAF_INDEX["groups"][ph["groups"][0]]["leaves"][0]
        return (f'Phân rã chi tiết: <a href="dfd.html#L1-{ph["code"]}">DFD mức 1 — tiến trình {ph["n"]}</a> '
                f'({len(ph["groups"])} chức năng cấp 2, {n_leaf} chức năng lá) · '
                f'<a href="phan_ra_chuc_nang.html#{first}">Sơ đồ phân rã</a> · '
                f'<a href="dac_ta_chuc_nang.html#{first}">Đặc tả &amp; truy vết từng chức năng lá</a>')
    role = next((r for r in ROLES if r["id"] == key), None)
    if role:
        n = sum(1 for lf in LEAF_INDEX["leaves"] if role["role"] in lf["roles"])
        return (f'Chi tiết: <a href="chuc_nang_cay.html#{role["id"]}">Cây chức năng của {html.escape(role["name"])}</a> '
                f'({n} chức năng lá, theo quyền trong code)')
    return ""


# ----------------------------------------------------------------------------- ERD (SVG)
BOX_W, HEAD_H, ROW_H, PAD_B = 300, 30, 20, 8
COLS_X = [110, 450, 870, 1210, 1630, 1970]  # chua le trai/phai cho duong vong cung cot
LAYOUT = {
    "users": (0, 100), "refresh_tokens": (1, 100), "revoked_tokens": (1, 280), "password_resets": (0, 320),
    "units": (2, 100), "staff": (3, 100), "locations": (2, 260), "rooms": (3, 260),
    "lecturers": (4, 100), "classes": (5, 100), "enrollments": (4, 280), "schedules": (5, 300),
    "students": (0, 680), "parents": (1, 680), "parent_students": (1, 860), "face_embeddings": (0, 980),
    "attendance_sessions": (2, 680), "attendance_records": (3, 680), "attendance_audits": (2, 900),
    "notifications": (4, 680), "audit_logs": (5, 680), "leave_requests": (3, 1010),
}
BADGE = {"PK": "#fde68a", "FK": "#bfdbfe", "UQ": "#e9d5ff"}


def box(name):
    col, y = LAYOUT[name]
    h = HEAD_H + ROW_H * len(META[name].columns) + PAD_B
    return COLS_X[col], y, BOX_W, h


def row_y(name, col_name):
    x, y, _w, _h = box(name)
    idx = [c.name for c in META[name].columns].index(col_name)
    return y + HEAD_H + ROW_H * idx + ROW_H / 2


def canvas_size() -> tuple[int, int]:
    return COLS_X[-1] + BOX_W + 110, max(box(n)[1] + box(n)[3] for n in META) + 50


def esc(s):
    return html.escape(str(s), quote=True)


def short_type(t: str) -> str:
    return (t.replace("TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP").replace("TIME WITHOUT TIME ZONE", "TIME")
             .replace("DOUBLE PRECISION", "FLOAT"))


def build_erd_svg() -> str:
    width, height = canvas_size()
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
             f'font-family="Segoe UI, DejaVu Sans, Arial, sans-serif">',
             '<title>ERD - FAMS</title>',
             f'<rect x="0" y="0" width="{width}" height="{height}" fill="white"/>']
    # Cum nhom
    for group, color, names in GROUPS:
        xs = [box(n) for n in names]
        x1 = min(b[0] for b in xs) - 18
        y1 = min(b[1] for b in xs) - 44
        x2 = max(b[0] + b[2] for b in xs) + 18
        y2 = max(b[1] + b[3] for b in xs) + 18
        parts.append(f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" rx="10" fill="white" '
                     f'stroke="{color}" stroke-dasharray="6,3" stroke-width="1.4"/>')
        parts.append(f'<text x="{(x1 + x2) / 2}" y="{y1 + 24}" text-anchor="middle" font-size="16" '
                     f'font-weight="600" fill="{color}">{esc(group)}</text>')
    # Duong noi khoa ngoai (ve truoc bang)
    labels = []
    edge_no = 0
    for child in ORDER:
        for c in META[child].columns:
            for fk in c.foreign_keys:
                parent = fk.column.table.name
                edge_no += 1
                px, py0, pw, _ph = box(parent)
                cx, cy0, cw, _ch = box(child)
                py, cy = row_y(parent, fk.column.name), row_y(child, c.name)
                color = GROUP_OF[parent][1]
                if cx > px + pw / 2:
                    sx, ex, sd, ed = px + pw, cx, 1, -1           # cha ben trai, con ben phai
                elif cx + cw / 2 < px:
                    sx, ex, sd, ed = px, cx + cw, -1, 1           # cha ben phai, con ben trai
                else:                                             # cung cot: vong ra mot ben
                    side = -1 if LAYOUT[parent][0] % 2 == 0 else 1
                    sx = px if side < 0 else px + pw
                    ex = cx if side < 0 else cx + cw
                    sd, ed = side, side
                bend = max(50, abs(ex - sx) * 0.45) + (edge_no % 5) * 6
                c1x, c2x = sx + sd * bend, ex + (ed * bend if ed == sd else ed * bend)
                if sd == ed:
                    c1x = sx + sd * (45 + (edge_no % 6) * 9)
                    c2x = ex + ed * (45 + (edge_no % 6) * 9)
                d = f"M{sx},{py} C{c1x},{py} {c2x},{cy} {ex},{cy}"
                parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.3" stroke-dasharray="5,3" opacity="0.75"/>')
                # Ky hieu: vach "1" phia cha, chan chim "N" phia con
                bx = sx + sd * 8
                parts.append(f'<line x1="{bx}" y1="{py - 6}" x2="{bx}" y2="{py + 6}" stroke="{color}" stroke-width="1.6"/>')
                one_to_one = c.name in unique_single(META[child])
                tip = ex + (ed * 12)
                if one_to_one:
                    parts.append(f'<line x1="{ex + ed * 8}" y1="{cy - 6}" x2="{ex + ed * 8}" y2="{cy + 6}" stroke="{color}" stroke-width="1.6"/>')
                else:
                    for dy in (-6, 0, 6):
                        parts.append(f'<line x1="{tip}" y1="{cy}" x2="{ex}" y2="{cy + dy}" stroke="{color}" stroke-width="1.4"/>')
                # nhan o giua duong cong (t = 0.5)
                mx = 0.125 * sx + 0.375 * c1x + 0.375 * c2x + 0.125 * ex
                my = 0.5 * py + 0.5 * cy
                labels.append((mx, my, "1 : 1" if one_to_one else "1 : N", color))
    for mx, my, text, color in labels:
        parts.append(f'<rect x="{mx - 17}" y="{my - 8}" width="34" height="15" rx="4" fill="white" opacity="0.9"/>'
                     f'<text x="{mx}" y="{my + 4}" text-anchor="middle" font-size="10.5" fill="{color}" font-weight="600">{text}</text>')
    # Bang
    for name in ORDER:
        x, y, w, h = box(name)
        group, color = GROUP_OF[name]
        table = META[name]
        parts.append(f'<g id="t-{name}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="white" stroke="{color}" stroke-width="1.6"/>')
        parts.append(f'<path d="M{x},{y + 6} a6,6 0 0 1 6,-6 h{w - 12} a6,6 0 0 1 6,6 v{HEAD_H - 6} h{-w} z" fill="{color}"/>')
        parts.append(f'<text x="{x + w / 2}" y="{y + 20}" text-anchor="middle" font-size="14" font-weight="700" fill="white">'
                     f'{esc(name)}<tspan font-size="10.5" font-weight="400" fill="#f1f5f9"> ({esc(TABLES[name]["title"])})</tspan></text>')
        for i, c in enumerate(table.columns):
            ry = y + HEAD_H + ROW_H * i
            if i % 2 == 1:
                parts.append(f'<rect x="{x + 1}" y="{ry}" width="{w - 2}" height="{ROW_H}" fill="#f8fafc"/>')
            keys = col_keys(table, c).split()
            tag = "PK" if "PK" in keys else ("FK" if any(k.startswith("FK") for k in keys) else ("UQ" if "UQ" in keys else ""))
            if tag:
                parts.append(f'<rect x="{x + 6}" y="{ry + 3}" width="24" height="14" rx="3" fill="{BADGE[tag]}"/>'
                             f'<text x="{x + 18}" y="{ry + 14}" text-anchor="middle" font-size="9" font-weight="700" fill="#1f2937">{tag}</text>')
            weight = "700" if c.primary_key else "400"
            parts.append(f'<text x="{x + 36}" y="{ry + 14.5}" font-size="12" font-weight="{weight}" fill="#111827">{esc(c.name)}</text>')
            parts.append(f'<text x="{x + w - 8}" y="{ry + 14.5}" text-anchor="end" font-size="9.5" fill="#64748b">'
                         f'{esc(short_type(col_type(c)))}{"" if c.nullable or c.primary_key else " NN"}</text>')
        parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)


def svg_to_png(svg_path: Path, png_path: Path, width: int, height: int, scale: float = 1.5) -> None:
    browsers = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
                Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")]
    exe = next((b for b in browsers if b.exists()), None) or shutil.which("chromium") or shutil.which("google-chrome")
    if not exe:
        print("Khong thay Edge/Chrome - bo qua erd.png")
        return
    # Ho so trinh duyet tam rieng, xoa ngay sau khi chup: khong dung ho so that cua nguoi dung.
    profile = Path(tempfile.mkdtemp(prefix="fams-erd-", dir=str(ROOT / ".tmp") if (ROOT / ".tmp").exists() else None))
    png_path.unlink(missing_ok=True)
    try:
        subprocess.run([str(exe), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                        f"--user-data-dir={profile}", f"--force-device-scale-factor={scale}",
                        f"--window-size={width},{height}", f"--screenshot={png_path}", svg_path.resolve().as_uri()],
                       check=True, timeout=120, capture_output=True)
        # Tren Windows trinh khoi dong thoat ngay, tien trinh chup chay tiep: cho anh ghi xong.
        for _ in range(120):
            if png_path.exists() and png_path.stat().st_size > 0:
                time.sleep(2)
                break
            time.sleep(0.5)
        else:
            print("Het thoi gian cho erd.png")
    finally:
        for _ in range(20):
            shutil.rmtree(profile, ignore_errors=True)
            if not profile.exists():
                break
            time.sleep(1)


# ----------------------------------------------------------------------------- ghep trang
def fill(template: str, values: dict) -> str:
    text = patch_template(template, (TPL / template).read_text(encoding="utf-8"))
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    if "{{" in text and "}}" in text.split("{{", 1)[1]:
        missing = text.split("{{", 1)[1].split("}}", 1)[0]
        if missing.isupper():
            raise SystemExit(f"{template}: con cho trong {{{{{missing}}}}}")
    return text


def main() -> None:
    check_data()
    OUT.mkdir(parents=True, exist_ok=True)
    n_tables = len(META)
    n_func = sum(1 for f in FLOWS if f["func"] and f["key"] != "master")
    n_roles = len(ROLES)
    flows_json = json.dumps([{**f, "links": flow_links(f)} for f in FLOWS], ensure_ascii=False)
    dumps = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")  # noqa: E731

    (OUT / "workflow_tong_quan.html").write_text(fill("workflow_tong_quan.html", {
        "TITLE": f"Sơ đồ quy trình tinh gọn - {PROJECT['short']}",
        "SUBTITLE": f"{esc(PROJECT['name'])} • {esc(PROJECT['org'])} • {esc(PROJECT['arch'])} • "
                    f"{n_func} phân hệ chức năng và {n_roles} nhóm đối tượng • Mỗi bước ghi rõ bảng CSDL đọc / ghi",
        "BADGE": f"GẮN VỚI CSDL {n_tables} BẢNG",
        "MODE_FUNC": f"1. QUY TRÌNH THEO PHÂN HỆ CHỨC NĂNG (PH1 → PH{n_func})",
        "MODE_ROLE": f"2. QUY TRÌNH THEO TỪNG NHÓM ĐỐI TƯỢNG ({n_roles} VAI TRÒ)",
        "FLOWS_JSON": flows_json.replace("</", "<\\/"),
    }), encoding="utf-8")

    (OUT / "csdl_chi_tiet.html").write_text(fill("csdl_chi_tiet.html", {
        "TITLE": f"Chi tiết bảng CSDL - {PROJECT['short']}",
        "TB_JSON": dumps(build_tb()), "DBMS": "PostgreSQL 16",
    }), encoding="utf-8")

    svg = build_erd_svg()
    (OUT / "erd.svg").write_text(svg, encoding="utf-8")
    legend = "".join(f'<span class="lg"><i style="background:{c}"></i>{esc(g)}</span>' for g, c, _n in GROUPS)
    map_rows = "".join(f"<tr><td><b>{code}</b></td><td>{esc(name)}</td><td>{', '.join(tables)}</td></tr>"
                       for code, name, tables in STORES)
    n_fk = sum(len(c.foreign_keys) for t in META.values() for c in t.columns)
    (OUT / "erd_csdl.html").write_text(fill("erd_csdl.html", {
        "TITLE": f"CSDL (ERD) - {PROJECT['short']}",
        "H1": f"Sơ đồ thực thể quan hệ (ERD) - {esc(PROJECT['short'])}",
        "SUBTITLE": f"{n_tables} bảng · {n_fk} khóa ngoại · PostgreSQL 16 + pgvector · nét đứt = khóa ngoại "
                    f"(màu theo bảng được tham chiếu), 1 : N (chân chim ở phía N), vạch đơn ở phía 1",
        "LEGEND": legend, "SVG": svg, "MAP_ROWS": map_rows,
    }), encoding="utf-8")

    (OUT / "chuc_nang_cay.html").write_text(fill("chuc_nang_cay.html", {
        "TITLE": f"Chức năng con & Giao diện — {PROJECT['short']}",
        "COURSE": PROJECT["course"],
        "H1": f"Chức năng con &amp; Giao diện<br>{esc(PROJECT['short'])} – {esc(PROJECT['org'])}",
        "NAVLABEL": "VAI TRÒ",
        "SIDEFOOT": ("Mỗi mục: Phân hệ (menu) → Chức năng lá → Dữ liệu vào (Input) → Kết quả ra (Output). Danh sách được "
                     "dựng tự động từ phân rã chức năng và QUYỀN THẬT trong code (require_roles, phạm vi Khoa/lớp). "
                     "Bấm mã chức năng để xem đặc tả và truy vết tới code."
                     if LEAF_INDEX else
                     "Mỗi mục thể hiện: Nhóm Menu → Chức năng con → Dữ liệu đầu vào (Input) → Kết quả đầu ra (Output). "
                     "Đăng nhập, đổi / quên mật khẩu dùng chung cho mọi vai trò (ghi ở mục Sinh viên)."),
        "DATA_JSON": dumps(build_roles()),
        "FOOTER": f"{esc(PROJECT['name'])} — {esc(PROJECT['org'])}.",
    }), encoding="utf-8")

    (OUT / "schema.sql").write_text(build_schema_sql(), encoding="utf-8")

    if "--png" in sys.argv:
        width, height = canvas_size()
        svg_to_png(OUT / "erd.svg", OUT / "erd.png", width, height)

    n_fn = sum(len(g["rows"]) for r in ROLES for g in r["groups"])
    print(f"Da ghi vao {OUT}: {n_tables} bang, {n_fk} khoa ngoai, {len(FLOWS)} quy trinh, {n_roles} vai tro, {n_fn} chuc nang con")


if __name__ == "__main__":
    main()
