"""Kiem tra lien ket cheo trong bo docs/so-do-luong-du-lieu-va-csdl (chay tu thu muc goc FAMS-SYSTEM):

    server/venv/Scripts/python docs/tools/check_links.py

Moi lien ket "<trang>.html#<neo>" phai tro toi neo co that: ma chuc nang la, so do DFD, ten bang, vai tro,
quy trinh. Thoat ma 1 neu co lien ket hong.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "so-do-luong-du-lieu-va-csdl"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    idx = json.loads((ROOT / "docs" / "tools" / "trace" / "leaf_index.json").read_text(encoding="utf-8"))
    leaf_ids = {lf["id"] for lf in idx["leaves"]}
    diagrams = set(idx["diagrams"])
    tables = set(re.findall(r'"vn": ?"(\w+)"', (OUT / "csdl_chi_tiet.html").read_text(encoding="utf-8")))
    roles = {"qt", "dt", "ctsv", "vpk", "ldk", "bn", "gv", "sv", "ph"}
    flows = {"master"} | {f"ph{i}" for i in range(1, 10)} | roles
    valid = {"dac_ta_chuc_nang.html": leaf_ids, "dfd.html": diagrams, "csdl_chi_tiet.html": tables,
             "chuc_nang_cay.html": roles, "phan_ra_chuc_nang.html": leaf_ids}
    link = re.compile(r'href=\\?["\']([\w_]+\.html)#([^"\'\\$]+)\\?["\']')
    local = re.compile(r'href=\\?"#([^"\\$]+)\\?"')
    bad, n = [], 0
    pages = sorted(OUT.glob("*.html")) + sorted((OUT / "dfd").glob("*.svg"))
    for f in pages:
        text = f.read_text(encoding="utf-8")
        for m in link.finditer(text):
            page, anchor = m.group(1), m.group(2)
            n += 1
            if page == "workflow_tong_quan.html":
                ok = anchor.split(":", 1)[0] in ("func", "role") and anchor.split(":", 1)[-1] in flows
            else:
                ok = anchor in valid.get(page, set())
            if not ok:
                bad.append((f.name, page, anchor))
        if f.name == "dfd.html" or f.suffix == ".svg":
            for m in local.finditer(text):
                n += 1
                if m.group(1) not in diagrams:
                    bad.append((f.name, "#", m.group(1)))
    expected = set(valid) | {"workflow_tong_quan.html", "erd_csdl.html", "chuan_hoa_csdl.html"}
    missing = sorted(expected - {p.name for p in OUT.glob("*.html")})
    print(f"trang: {len(pages)} | lien ket co neo da kiem: {n} | hong: {len(bad)} | trang thieu: {missing}")
    for b in bad[:20]:
        print("  HONG", b)
    return 1 if bad or missing else 0


if __name__ == "__main__":
    sys.exit(main())
