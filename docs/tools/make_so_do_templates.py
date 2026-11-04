"""Tach khung giao dien (CSS + ham ve) tu bo "so-do-luong-du-lieu-va-csdl" goc thanh mau co cho trong.

Chay MOT lan khi muon lay lai giao dien tu bo goc:
    python docs/tools/make_so_do_templates.py <thu muc bo goc>
Ket qua: docs/tools/so_do_templates/*.html, gen_so_do_csdl.py dien du lieu FAMS vao {{...}}.
"""
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "so_do_templates"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"[{label}] can dung 1 cho '{old[:60]}...', tim thay {n}")
    return text.replace(old, new)


def replace_json_const(text: str, name: str, placeholder: str, label: str) -> str:
    """Thay `const NAME = [ ...json... ];` bang placeholder (doc JSON de biet chinh xac diem ket thuc)."""
    m = re.search(rf"const {name}\s*=\s*", text)
    if not m:
        raise SystemExit(f"[{label}] khong thay const {name}")
    start = m.end()
    if text[start] == "[" and name == "DATA":
        # DATA viet dang JS (khoa khong co ngoac kep) - tim "];" dong mang o cap 0.
        depth, i = 0, start
        while True:
            ch = text[i]
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
            elif ch in "\"'`":
                quote = ch
                i += 1
                while text[i] != quote:
                    i += 2 if text[i] == "\\" else 1
            i += 1
    else:
        _obj, length = json.JSONDecoder().raw_decode(text[start:])
        end = start + length
    return text[:start] + placeholder + text[end:]


def main(src_dir: str) -> None:
    src = Path(src_dir)
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- So do quy trinh
    s = (src / "workflow_tong_quan.html").read_text(encoding="utf-8")
    s = re.sub(r"<title>.*?</title>", "<title>{{TITLE}}</title>", s, count=1, flags=re.S)
    s = re.sub(r'(<div class="sbt">).*?(</div>)', r"\1{{SUBTITLE}}\2", s, count=1, flags=re.S)
    s = re.sub(r'(<span class="badge">).*?(</span>)', r"\1{{BADGE}}\2", s, count=1, flags=re.S)
    s = re.sub(r"(id=\"m-func\" onclick=\"setMode\('func'\)\">).*?(</button>)", r"\1{{MODE_FUNC}}\2", s, count=1, flags=re.S)
    s = re.sub(r"(id=\"m-role\" onclick=\"setMode\('role'\)\">).*?(</button>)", r"\1{{MODE_ROLE}}\2", s, count=1, flags=re.S)
    s = replace_json_const(s, "FLOWS", "{{FLOWS_JSON}}", "workflow")
    (OUT / "workflow_tong_quan.html").write_text(s, encoding="utf-8")

    # ---- Chi tiet bang
    s = (src / "csdl_chi_tiet.html").read_text(encoding="utf-8")
    s = re.sub(r"<title>.*?</title>", "<title>{{TITLE}}</title>", s, count=1, flags=re.S)
    s = replace_json_const(s, "TB", "{{TB_JSON}}", "csdl_chi_tiet")
    s = replace_once(s, "Câu lệnh tạo bảng (MySQL)", "Câu lệnh tạo bảng ({{DBMS}})", "csdl_chi_tiet")
    s = replace_once(s, "<p>${t.desc}</p>", "<p><b>${t.title}</b> — ${t.desc}</p>", "csdl_chi_tiet")
    (OUT / "csdl_chi_tiet.html").write_text(s, encoding="utf-8")

    # ---- ERD
    s = (src / "erd_csdl.html").read_text(encoding="utf-8")
    s = re.sub(r"<title>.*?</title>", "<title>{{TITLE}}</title>", s, count=1, flags=re.S)
    s = re.sub(r'(<div class="wrap"><h1>).*?(</h1>)', r"\1{{H1}}\2", s, count=1, flags=re.S)
    s = re.sub(r'(<div class="sbt">).*?(</div>)', r"\1{{SUBTITLE}}\2", s, count=1, flags=re.S)
    s = re.sub(r'(<div>)(<span class="lg">.*?)(</div>\s*<div class="canvas")', r"\1{{LEGEND}}\3", s, count=1, flags=re.S)
    s = re.sub(r"<svg.*?</svg>", "{{SVG}}", s, count=1, flags=re.S)
    s = re.sub(r"(<tr><th>Kho DFD</th><th>Tên kho</th><th>Các bảng CSDL</th></tr>).*?(</table>)",
               r"\1{{MAP_ROWS}}\2", s, count=1, flags=re.S)
    (OUT / "erd_csdl.html").write_text(s, encoding="utf-8")

    # ---- Cay chuc nang
    s = (src / "chuc_nang_cay.html").read_text(encoding="utf-8")
    s = re.sub(r"<title>.*?</title>", "<title>{{TITLE}}</title>", s, count=1, flags=re.S)
    s = re.sub(r'(<div class="tag">).*?(</div>)', r"\1{{COURSE}}\2", s, count=1, flags=re.S)
    s = re.sub(r'(<div class="brand">\s*<div class="tag">\{\{COURSE\}\}</div>\s*<h1>).*?(</h1>)', r"\1{{H1}}\2", s, count=1, flags=re.S)
    s = re.sub(r'(<div class="navlabel">).*?(</div>)', r"\1{{NAVLABEL}}\2", s, count=1, flags=re.S)
    s = re.sub(r'(<div class="sidebar-foot">).*?(</div>)', r"\1{{SIDEFOOT}}\2", s, count=1, flags=re.S)
    s = replace_json_const(s, "DATA", "{{DATA_JSON}}", "chuc_nang_cay")
    s = re.sub(r'(<footer class="page">).*?(</footer>)', r"\1{{FOOTER}}\2", s, count=1, flags=re.S)
    (OUT / "chuc_nang_cay.html").write_text(s, encoding="utf-8")

    for f in sorted(OUT.glob("*.html")):
        holes = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", f.read_text(encoding="utf-8"))))
        print(f"{f.name}: {holes}")


if __name__ == "__main__":
    main(sys.argv[1])
