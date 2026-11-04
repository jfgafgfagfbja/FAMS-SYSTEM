"""Xuat tai lieu API tu chinh server: docs/api/openapi.json + docs/api/ENDPOINTS.md.

Chay lai moi khi doi endpoint (CI co the so sanh de phat hien tai lieu cu):
    server/venv/Scripts/python scripts/export_openapi.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.main import app  # noqa: E402

OUT = ROOT / "docs" / "api"
METHOD_ORDER = {"get": 0, "post": 1, "patch": 2, "put": 3, "delete": 4}


def first_line(text: str | None) -> str:
    return (text or "").strip().splitlines()[0].strip() if text and text.strip() else ""


def main() -> None:
    spec = app.openapi()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "openapi.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")

    by_tag: dict[str, list[tuple[str, str, str, str, str]]] = {}
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            tag = (op.get("tags") or ["(khac)"])[0]
            secured = "Bearer" if op.get("security") else "—"
            params = ", ".join(
                f"`{p['name']}`" for p in op.get("parameters", []) if p.get("in") == "query")
            body = op.get("requestBody", {}).get("content", {})
            kind = "form" if "application/x-www-form-urlencoded" in body else (
                "multipart" if "multipart/form-data" in body else ("JSON" if body else ""))
            summary = first_line(op.get("description")) or op.get("summary", "")
            by_tag.setdefault(tag, []).append((method.upper(), path, secured,
                                                ", ".join(x for x in (kind, params) if x), summary))

    tag_desc = {t["name"]: t.get("description", "") for t in spec.get("tags", [])}
    lines = [
        "# Danh sach endpoint (sinh tu dong)",
        "",
        f"> Sinh boi `scripts/export_openapi.py` tu server phien ban {spec['info']['version']}. "
        "Dac ta day du: [openapi.json](openapi.json) (mo bang Swagger Editor) hoac `/docs` khi server chay.",
        "",
        f"Tong: **{sum(len(v) for v in by_tag.values())}** endpoint.",
        "",
    ]
    order = [t["name"] for t in spec.get("tags", [])] + sorted(set(by_tag) - {t["name"] for t in spec.get("tags", [])})
    for tag in order:
        rows = by_tag.get(tag)
        if not rows:
            continue
        rows.sort(key=lambda r: (r[1], METHOD_ORDER.get(r[0].lower(), 9)))
        lines += [f"## {tag}", "", tag_desc.get(tag, ""), "",
                  "| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |", "|---|---|---|---|---|"]
        lines += [f"| {m} | `{p}` | {s} | {k} | {d} |" for m, p, s, k, d in rows]
        lines.append("")
    (OUT / "ENDPOINTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Da ghi {OUT / 'openapi.json'} va {OUT / 'ENDPOINTS.md'}")


if __name__ == "__main__":
    main()
